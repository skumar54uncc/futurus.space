"""
Adapter between Futurus and MiroFish core.
MiroFish is located at /mirofish (mounted from mirofish-core/).
This adapter:
1. Initializes MiroFish with our seed + personas
2. Runs the simulation turn by turn
3. Extracts events from each turn
4. Streams results as an async generator
"""
import json
import sys
import os

sys.path.insert(0, "/mirofish")
sys.path.insert(0, "/mirofish/backend")

import asyncio
from simulation_engine.cost_governor import CostGovernor
from typing import AsyncGenerator
import structlog

from core.config import settings

logger = structlog.get_logger()


class MiroFishAdapter:
    def __init__(self, seed: dict, personas: list, cost_governor: CostGovernor):
        self.seed = seed
        self.personas = personas
        self.cost_governor = cost_governor
        self._engine = None

    async def run(self, max_turns: int) -> AsyncGenerator[dict, None]:
        try:
            from backend.app import create_simulation_engine

            self._engine = await create_simulation_engine(
                seed=self.seed,
                agent_configs=self._personas_to_mirofish_format(),
                config={
                    "max_turns": max_turns,
                    "llm_api_key": settings.openai_compatible_llm_key()
                    or os.getenv("LLM_API_KEY", ""),
                    "llm_base_url": settings.openai_compatible_llm_base()
                    or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
                    "llm_model": os.getenv("LLM_MODEL_TIER2") or settings.llm_model_tier2,
                    "zep_api_key": os.getenv("ZEP_API_KEY") or settings.zep_api_key,
                },
            )
        except ImportError:
            logger.warning("mirofish_import_failed_using_mock")
            async for result in self._run_mock_simulation(max_turns):
                yield result
            return

        for turn in range(1, max_turns + 1):
            if self.cost_governor.is_over_limit():
                break

            try:
                turn_result = await asyncio.wait_for(
                    self._engine.step(), timeout=120.0
                )
                events = self._extract_events(turn_result)
                self.cost_governor.record_turn_cost(
                    turn_result.get("llm_cost_usd", 0.05)
                )
                yield {
                    "turn": turn,
                    "agents_active": turn_result.get(
                        "active_agents", len(self.personas)
                    ),
                    "events": events,
                    "raw": turn_result,
                }
            except asyncio.TimeoutError:
                logger.warning("turn_timeout", turn=turn)
                continue
            except Exception as e:
                logger.error("turn_error", turn=turn, error=str(e))
                continue

    def _personas_to_mirofish_format(self) -> list:
        return [
            {
                "name": p["name"],
                "personality": " ".join(p.get("personality", [])),
                "background": (
                    f"I am a {p['segment']} customer. "
                    f"My main motivation: {p.get('main_motivation', '')}. "
                    f"My main objection: {p.get('main_objection', '')}. "
                    f"I adopt when: {p.get('trigger_to_adopt', '')}. "
                    f"I churn when: {p.get('trigger_to_churn', '')}."
                ),
                "attributes": {
                    "budget_sensitivity": p.get("budget_sensitivity", 0.5),
                    "influence_score": p.get("influence_score", 0.3),
                    "decision_speed": p.get("decision_speed", "medium"),
                    "segment": p["segment"],
                    "status": "prospect",
                },
            }
            for p in self.personas
        ]

    def _extract_events(self, turn_result: dict) -> list:
        events = []
        for interaction in turn_result.get("interactions", []):
            event_type = self._classify_event(interaction)
            if event_type:
                events.append(
                    {
                        "agent_name": interaction.get("agent_name", "Unknown"),
                        "segment": interaction.get("agent_attributes", {}).get(
                            "segment", "unknown"
                        ),
                        "event_type": event_type,
                        "description": interaction.get("content", "")[:200],
                    }
                )
        return events

    def _classify_event(self, interaction: dict) -> str | None:
        content = interaction.get("content", "").lower()
        status_change = interaction.get("status_change", "")

        if status_change == "adopted" or any(
            w in content for w in ["sign up", "subscribe", "try it", "purchased"]
        ):
            return "adopted"
        if status_change == "churned" or any(
            w in content
            for w in ["cancel", "unsubscribe", "leaving", "too expensive"]
        ):
            return "churned"
        if any(w in content for w in ["told", "recommended", "shared", "referred"]):
            return "referred"
        if any(w in content for w in ["not for me", "pass", "won't", "decline"]):
            return "rejected"
        return None

    @staticmethod
    def _assign_tiers(personas: list) -> list:
        """Sort agents by influence_score desc, assign _tier (1/2/3) to each."""
        try:
            from core.config import settings
            tier1_count = settings.agent_tier1_count
            tier2_count = settings.agent_tier2_count
        except Exception:
            tier1_count = 50
            tier2_count = 200

        sorted_personas = sorted(
            personas, key=lambda p: p.get("influence_score", 0.0), reverse=True
        )
        for i, p in enumerate(sorted_personas):
            if i < tier1_count:
                p["_tier"] = 1
            elif i < tier1_count + tier2_count:
                p["_tier"] = 2
            else:
                p["_tier"] = 3
        return sorted_personas

    @staticmethod
    async def _llm_prospect_decision(
        agent: dict, turn: int, adoption_rate: float
    ) -> dict:
        """
        LLM-powered decision for a Tier 1/2 prospect agent.
        Always falls back to crowd_agent_decision() — never raises.
        """
        from services.llm_router import (
            call_llm,
            crowd_agent_decision,
            CrowdAgentSkip,
            AllProvidersExhausted,
        )

        budget_sens = agent.get("budget_sensitivity", 0.5)
        price_sens = (
            "high" if budget_sens > 0.65 else ("low" if budget_sens < 0.35 else "medium")
        )

        prompt = (
            f"Simulate customer {agent['name']} ({agent['segment']}) at turn {turn}/40. "
            f"Market adoption so far: {adoption_rate:.0%}. "
            f"Motivation: {agent.get('main_motivation', 'N/A')}. "
            f"Objection: {agent.get('main_objection', 'N/A')}. "
            f"Adopts when: {agent.get('trigger_to_adopt', 'N/A')}. "
            'Reply ONLY with JSON: {"event_type":"adopted|rejected|deferred|referred","description":"<1 sentence>"}'
        )

        try:
            content = await call_llm(
                messages=[{"role": "user", "content": prompt}],
                agent_tier=agent["_tier"],
                temperature=0.85,
                max_tokens=80,
                json_mode=True,
            )
            data = json.loads(content)
            event_type = data.get("event_type", "deferred")
            if event_type not in ("adopted", "rejected", "deferred", "referred"):
                event_type = "deferred"
            return {
                "event_type": event_type,
                "event_description": str(data.get("description", ""))[:200],
            }
        except (CrowdAgentSkip, AllProvidersExhausted, Exception) as exc:
            if not isinstance(exc, CrowdAgentSkip):
                logger.warning(
                    "llm_agent_fallback_to_crowd",
                    agent=agent["name"],
                    error=str(exc)[:120],
                )
            result = crowd_agent_decision(
                segment=agent["segment"],
                turn=turn,
                current_adoption_rate=adoption_rate,
                price_sensitivity=price_sens,
            )
            return {
                "event_type": result["event_type"],
                "event_description": result["event_description"],
            }

    async def _run_mock_simulation(
        self, max_turns: int
    ) -> AsyncGenerator[dict, None]:
        import random
        from services.llm_router import crowd_agent_decision

        # Assign LLM tiers before the loop
        personas = self._assign_tiers(list(self.personas))
        total_agents = len(personas)
        adopted_agents: set[str] = set()
        churned_agents: set[str] = set()

        # Build segment lookup for event emission
        segment_of: dict[str, str] = {p["name"]: p["segment"] for p in personas}

        for turn in range(1, max_turns + 1):
            turn_events = []
            current_adoption_rate = len(adopted_agents) / max(1, total_agents)

            # ── Collect prospects that need LLM calls this turn ───────────────
            tier1_prospects = []
            tier2_llm_prospects = []
            for p in personas:
                aid = p["name"]
                if aid in adopted_agents or aid in churned_agents:
                    continue
                if p["_tier"] == 1:
                    tier1_prospects.append(p)
                elif p["_tier"] == 2 and turn % 4 == 0:
                    tier2_llm_prospects.append(p)

            # ── Fire LLM calls concurrently per tier ──────────────────────────
            tier1_decisions: dict[str, dict] = {}
            tier2_decisions: dict[str, dict] = {}

            if tier1_prospects:
                results = await asyncio.gather(
                    *[
                        self._llm_prospect_decision(p, turn, current_adoption_rate)
                        for p in tier1_prospects
                    ],
                    return_exceptions=True,
                )
                for p, res in zip(tier1_prospects, results):
                    if isinstance(res, dict):
                        tier1_decisions[p["name"]] = res

            if tier2_llm_prospects:
                results = await asyncio.gather(
                    *[
                        self._llm_prospect_decision(p, turn, current_adoption_rate)
                        for p in tier2_llm_prospects
                    ],
                    return_exceptions=True,
                )
                for p, res in zip(tier2_llm_prospects, results):
                    if isinstance(res, dict):
                        tier2_decisions[p["name"]] = res

            # ── Process every agent ───────────────────────────────────────────
            for agent in personas:
                aid = agent["name"]
                seg = segment_of[aid]
                tier = agent["_tier"]
                budget_sens = agent.get("budget_sensitivity", 0.5)
                price_sens = (
                    "high"
                    if budget_sens > 0.65
                    else ("low" if budget_sens < 0.35 else "medium")
                )

                # Already adopted → churn / refer check (no LLM needed)
                if aid in adopted_agents:
                    churn_prob = budget_sens * 0.04
                    if random.random() < churn_prob:
                        churned_agents.add(aid)
                        adopted_agents.discard(aid)
                        turn_events.append({
                            "agent_name": aid,
                            "segment": seg,
                            "event_type": "churned",
                            "description": agent.get(
                                "trigger_to_churn",
                                "Product didn't meet expectations.",
                            ),
                        })
                    elif random.random() < agent.get("influence_score", 0.3) * 0.1:
                        turn_events.append({
                            "agent_name": aid,
                            "segment": seg,
                            "event_type": "referred",
                            "description": "Recommended the product to a colleague.",
                        })
                    continue

                # Already churned → skip
                if aid in churned_agents:
                    continue

                # Prospect → tiered decision
                if tier == 1 and aid in tier1_decisions:
                    decision = tier1_decisions[aid]
                elif tier == 2 and aid in tier2_decisions:
                    decision = tier2_decisions[aid]
                else:
                    # Tier 3 always, or Tier 2 on non-LLM turns
                    res = crowd_agent_decision(
                        seg, turn, current_adoption_rate, price_sens
                    )
                    decision = {
                        "event_type": res["event_type"],
                        "event_description": res["event_description"],
                    }

                event_type = decision["event_type"]

                # Track state changes
                if event_type in ("adopted", "referred"):
                    adopted_agents.add(aid)

                # Only log meaningful events (skip "deferred" — agent stays prospect)
                if event_type in ("adopted", "rejected", "referred"):
                    turn_events.append({
                        "agent_name": aid,
                        "segment": seg,
                        "event_type": event_type,
                        "description": decision["event_description"],
                    })

            # Cost: ~$0.001 per Tier 1 call, ~$0.0003 per Tier 2 call
            self.cost_governor.record_turn_cost(
                0.001 * len(tier1_prospects) + 0.0003 * len(tier2_llm_prospects)
            )
            yield {
                "turn": turn,
                "agents_active": total_agents - len(churned_agents),
                "events": turn_events,
            }

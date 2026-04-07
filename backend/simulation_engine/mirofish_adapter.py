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
import re
import sys
import os
import random
from collections import defaultdict

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
        self.timeout_count = 0

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
                step_start = asyncio.get_running_loop().time()
                turn_result = await asyncio.wait_for(
                    self._engine.step(), timeout=float(settings.mirofish_step_timeout_seconds)
                )
                step_elapsed_ms = round((asyncio.get_running_loop().time() - step_start) * 1000.0, 2)
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
                    "turn_wall_time_ms": step_elapsed_ms,
                }
            except asyncio.TimeoutError:
                logger.warning("turn_timeout", turn=turn)
                self.timeout_count += 1
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
    def _parse_distribution(llm_response: str) -> dict:
        """Safely parse probability distribution from LLM response."""
        cleaned = re.sub(r'```(?:json)?\s*', '', llm_response).strip().rstrip('`').strip()
        try:
            dist = json.loads(cleaned)
        except json.JSONDecodeError:
            return {"adopted": 0.25, "deferred": 0.25, "rejected": 0.25, "referred": 0.25}
        valid_keys = {"adopted", "rejected", "deferred", "referred"}
        filtered = {k: float(v) for k, v in dist.items() if k in valid_keys and isinstance(v, (int, float))}
        if not filtered:
            return {"adopted": 0.25, "deferred": 0.25, "rejected": 0.25, "referred": 0.25}
        total = sum(filtered.values())
        if total <= 0:
            return {"adopted": 0.25, "deferred": 0.25, "rejected": 0.25, "referred": 0.25}
        return {k: v / total for k, v in filtered.items()}

    @staticmethod
    async def _llm_archetype_decision(
        representative: dict, group_size: int, turn: int, adoption_rate: float, tier: int
    ) -> dict:
        """
        LLM-powered decision for an archetype (segment group).
        Returns a probability distribution over actions for all agents in this archetype.
        Falls back to uniform distribution on any error.
        """
        from services.llm_router import (
            call_llm,
            CrowdAgentSkip,
            AllProvidersExhausted,
        )

        prompt = (
            f"You represent an archetype of {group_size} consumers who share these traits.\n"
            f"Segment: {representative['segment']}. Turn: {turn}/40.\n"
            f"Market adoption so far: {adoption_rate:.0%}.\n"
            f"Motivation: {representative.get('main_motivation', 'N/A')}.\n"
            f"Objection: {representative.get('main_objection', 'N/A')}.\n"
            f"Adopts when: {representative.get('trigger_to_adopt', 'N/A')}.\n"
            "Given the current market state, return a JSON probability distribution "
            "over possible actions. Probabilities must sum to 1.0.\n"
            'Reply ONLY with JSON: {"adopted": 0.XX, "deferred": 0.XX, "rejected": 0.XX, "referred": 0.XX}'
        )

        try:
            content = await call_llm(
                messages=[{"role": "user", "content": prompt}],
                agent_tier=tier,
                temperature=0.85,
                max_tokens=300,
                json_mode=True,
            )
            return MiroFishAdapter._parse_distribution(content)
        except (CrowdAgentSkip, AllProvidersExhausted, Exception) as exc:
            if not isinstance(exc, CrowdAgentSkip):
                logger.warning(
                    "llm_archetype_fallback",
                    segment=representative.get("segment"),
                    error=str(exc)[:120],
                )
            return {"adopted": 0.25, "deferred": 0.25, "rejected": 0.25, "referred": 0.25}

    @staticmethod
    def _apply_distribution(agents: list, distribution: dict) -> dict[str, dict]:
        """Apply a probability distribution to a group of agents via weighted sampling."""
        actions = list(distribution.keys())
        weights = list(distribution.values())
        decisions: dict[str, dict] = {}

        # Pre-fetch a description bank for each action type
        _DESCRIPTIONS = {
            "adopted": [
                "Signed up after seeing the value proposition.",
                "The benefits outweighed the initial hesitation.",
                "Word of mouth was the tipping point.",
                "The pricing felt right for the value offered.",
            ],
            "rejected": [
                "Not convinced enough at this stage.",
                "The price point was a dealbreaker.",
                "Compared with alternatives and chose a competitor.",
                "Not ready to commit right now.",
            ],
            "deferred": [
                "Interested but not ready to decide yet.",
                "Waiting for more social proof before committing.",
                "Put the decision off — too busy right now.",
                "Bookmarked it to revisit later.",
            ],
            "referred": [
                "Recommended it to colleagues immediately.",
                "Shared it on their social channels.",
                "Brought it up in a team meeting.",
                "Left a positive review and tagged the brand.",
            ],
        }

        for agent in agents:
            chosen = random.choices(actions, weights=weights, k=1)[0]
            desc_list = _DESCRIPTIONS.get(chosen, _DESCRIPTIONS["deferred"])
            decisions[agent["name"]] = {
                "event_type": chosen,
                "event_description": random.choice(desc_list),
            }
        return decisions

    async def _run_mock_simulation(
        self, max_turns: int
    ) -> AsyncGenerator[dict, None]:
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

            # ── Collect prospects by archetype (segment) for LLM calls ────────
            tier1_by_segment: dict[str, list[dict]] = defaultdict(list)
            tier2_by_segment: dict[str, list[dict]] = defaultdict(list)
            for p in personas:
                aid = p["name"]
                if aid in adopted_agents or aid in churned_agents:
                    continue
                if p["_tier"] == 1:
                    tier1_by_segment[p["segment"]].append(p)
                elif p["_tier"] == 2 and turn % 4 == 0:
                    tier2_by_segment[p["segment"]].append(p)

            # ── Fire 1 LLM call per archetype (not per agent) ────────────────
            tier1_decisions: dict[str, dict] = {}
            tier2_decisions: dict[str, dict] = {}
            archetype_calls = 0

            if tier1_by_segment:
                async def _t1_archetype_call(seg: str, agents: list[dict]) -> tuple[str, dict]:
                    dist = await self._llm_archetype_decision(
                        agents[0], len(agents), turn, current_adoption_rate, tier=1
                    )
                    return seg, dist

                results = await asyncio.gather(
                    *[_t1_archetype_call(seg, agents) for seg, agents in tier1_by_segment.items()],
                    return_exceptions=True,
                )
                for res in results:
                    if isinstance(res, tuple):
                        seg, dist = res
                        tier1_decisions.update(self._apply_distribution(tier1_by_segment[seg], dist))
                        archetype_calls += 1

            if tier2_by_segment:
                async def _t2_archetype_call(seg: str, agents: list[dict]) -> tuple[str, dict]:
                    dist = await self._llm_archetype_decision(
                        agents[0], len(agents), turn, current_adoption_rate, tier=2
                    )
                    return seg, dist

                results = await asyncio.gather(
                    *[_t2_archetype_call(seg, agents) for seg, agents in tier2_by_segment.items()],
                    return_exceptions=True,
                )
                for res in results:
                    if isinstance(res, tuple):
                        seg, dist = res
                        tier2_decisions.update(self._apply_distribution(tier2_by_segment[seg], dist))
                        archetype_calls += 1

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

            # Cost per archetype call (not per agent) — ~$0.001 per call
            self.cost_governor.record_turn_cost(0.001 * archetype_calls)
            yield {
                "turn": turn,
                "agents_active": total_agents - len(churned_agents),
                "events": turn_events,
            }

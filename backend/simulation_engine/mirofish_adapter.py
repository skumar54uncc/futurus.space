"""
Adapter between Futurus and MiroFish core.
MiroFish is located at /mirofish (mounted from mirofish-core/).
This adapter:
1. Initializes MiroFish with our seed + personas
2. Runs the simulation turn by turn
3. Extracts events from each turn
4. Streams results as an async generator
"""
import sys
import os

sys.path.insert(0, "/mirofish")
sys.path.insert(0, "/mirofish/backend")

import asyncio
from simulation_engine.cost_governor import CostGovernor
from typing import AsyncGenerator
import structlog

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
                    "llm_api_key": os.getenv("LLM_API_KEY"),
                    "llm_base_url": os.getenv("LLM_BASE_URL"),
                    "llm_model": os.getenv("LLM_MODEL_TIER2"),
                    "zep_api_key": os.getenv("ZEP_API_KEY"),
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

    async def _run_mock_simulation(
        self, max_turns: int
    ) -> AsyncGenerator[dict, None]:
        import random

        total_agents = len(self.personas)
        adopted_agents: set[str] = set()
        churned_agents: set[str] = set()

        segment_groups: dict[str, list] = {}
        for p in self.personas:
            seg = p["segment"]
            if seg not in segment_groups:
                segment_groups[seg] = []
            segment_groups[seg].append(p)

        decision_speed_map = {
            "fast": 8,
            "medium": 18,
            "slow": 30,
            "fast-if-free": 10,
        }

        for turn in range(1, max_turns + 1):
            await asyncio.sleep(0.3)
            turn_events = []

            for seg, agents in segment_groups.items():
                for agent in agents:
                    agent_id = agent["name"]
                    if agent_id in adopted_agents:
                        churn_prob = agent.get("budget_sensitivity", 0.5) * 0.04
                        if random.random() < churn_prob:
                            churned_agents.add(agent_id)
                            adopted_agents.discard(agent_id)
                            turn_events.append(
                                {
                                    "agent_name": agent["name"],
                                    "segment": seg,
                                    "event_type": "churned",
                                    "description": agent.get(
                                        "trigger_to_churn",
                                        "Product didn't meet expectations.",
                                    ),
                                }
                            )
                        elif (
                            random.random()
                            < agent.get("influence_score", 0.3) * 0.1
                        ):
                            turn_events.append(
                                {
                                    "agent_name": agent["name"],
                                    "segment": seg,
                                    "event_type": "referred",
                                    "description": "Recommended the product to a colleague.",
                                }
                            )
                    elif agent_id not in churned_agents:
                        wom_factor = (
                            1
                            + (len(adopted_agents) / max(1, total_agents)) * 0.5
                        )
                        speed = decision_speed_map.get(
                            agent.get("decision_speed", "medium"), 18
                        )
                        adopt_prob = (1 / speed) * wom_factor * (turn / max_turns)
                        if random.random() < adopt_prob:
                            adopted_agents.add(agent_id)
                            turn_events.append(
                                {
                                    "agent_name": agent["name"],
                                    "segment": seg,
                                    "event_type": "adopted",
                                    "description": agent.get(
                                        "trigger_to_adopt",
                                        "Saw value proposition, signed up.",
                                    ),
                                }
                            )
                        elif random.random() < 0.02:
                            turn_events.append(
                                {
                                    "agent_name": agent["name"],
                                    "segment": seg,
                                    "event_type": "rejected",
                                    "description": agent.get(
                                        "main_objection",
                                        "Not interested at this time.",
                                    ),
                                }
                            )

            self.cost_governor.record_turn_cost(0.02)
            yield {
                "turn": turn,
                "agents_active": total_agents - len(churned_agents),
                "events": turn_events,
            }

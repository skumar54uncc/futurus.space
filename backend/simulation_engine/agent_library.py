"""60 pre-built consumer agent personas across different verticals and behavior types."""
import json
from pathlib import Path
from typing import Optional

PERSONA_DIR = Path(__file__).resolve().parent.parent.parent / "simulation" / "persona_archetypes"


def load_archetype_library(vertical: str) -> list[dict]:
    archetype_path = PERSONA_DIR / f"{vertical}.json"
    if archetype_path.exists():
        with open(archetype_path) as f:
            return json.load(f)
    return get_universal_archetypes()


def get_all_verticals() -> list[str]:
    return ["saas", "consumer_app", "marketplace", "physical_product", "service_business", "enterprise"]


def get_universal_archetypes() -> list[dict]:
    return [
        {
            "segment": "innovator",
            "natural_prevalence": 5,
            "budget_sensitivity": 0.1,
            "influence_score": 0.9,
            "decision_speed": "fast",
            "personality_traits": ["visionary", "risk-taker", "tech-savvy"],
        },
        {
            "segment": "early_adopter",
            "natural_prevalence": 13,
            "budget_sensitivity": 0.25,
            "influence_score": 0.8,
            "decision_speed": "fast",
            "personality_traits": ["opinion-leader", "status-conscious", "networked"],
        },
        {
            "segment": "early_majority",
            "natural_prevalence": 34,
            "budget_sensitivity": 0.5,
            "influence_score": 0.4,
            "decision_speed": "medium",
            "personality_traits": ["pragmatic", "deliberate", "social-proof-driven"],
        },
        {
            "segment": "late_majority",
            "natural_prevalence": 34,
            "budget_sensitivity": 0.7,
            "influence_score": 0.2,
            "decision_speed": "slow",
            "personality_traits": ["skeptical", "price-sensitive", "tradition-oriented"],
        },
        {
            "segment": "laggard",
            "natural_prevalence": 14,
            "budget_sensitivity": 0.9,
            "influence_score": 0.05,
            "decision_speed": "slow",
            "personality_traits": ["resistant", "suspicious", "set-in-ways"],
        },
    ]


def get_segment_description(segment: str) -> str:
    descriptions = {
        "innovator": "Technology enthusiasts who pursue new products aggressively. They want to be first.",
        "early_adopter": "Visionaries who match emerging tech to strategic opportunities. Willing to take risks for competitive advantage.",
        "early_majority": "Pragmatists who adopt once technology is proven. They want references and case studies.",
        "late_majority": "Conservatives who wait until technology is established and support structures are mature.",
        "laggard": "Skeptics who avoid new technology until forced to adopt. Highly resistant to change.",
        "power_user": "Heavy users who push products to their limits. High expectations, vocal feedback.",
        "price_sensitive": "Buyers driven primarily by cost. Will switch for a lower price.",
        "enterprise_champion": "Internal advocates who push for adoption within large organizations.",
    }
    return descriptions.get(segment, f"Customer segment: {segment}")

"""
Generates realistic customer personas based on the business idea, location, and target market.
Uses LLM to create real-world demographic segments (age groups, occupations, lifestyles)
instead of abstract marketing archetypes.
"""
import json
import random
from openai import AsyncOpenAI
from core.config import settings

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


async def generate_personas(
    vertical: str,
    target_market: str,
    idea_description: str,
    agent_count: int,
) -> list[dict]:
    archetypes = await _generate_real_world_segments(
        vertical, target_market, idea_description, agent_count
    )

    personas = []
    for archetype in archetypes:
        count = archetype.get("count", 1)
        for i in range(count):
            persona = _instantiate_persona(archetype, i)
            personas.append(persona)

    return personas


async def _generate_real_world_segments(
    vertical: str, target_market: str, idea: str, agent_count: int
) -> list[dict]:
    prompt = f"""You are a market research expert. Generate realistic customer segments for this business idea.
These should be REAL people you'd find in the actual target market — not abstract marketing terms.

Business idea: {idea}
Target market: {target_market}
Business type: {vertical}
Total customers to simulate: {agent_count}

Create 8-12 customer segments. Each segment should be a recognizable real-world group like:
- "College Students (18-22)" not "early_adopter"
- "Working Parents (30-45)" not "pragmatist"
- "Retired Seniors (65+)" not "late_majority"
- "Remote Workers" not "power_user"
- "Local Office Workers" not "price_sensitive"

For each segment, consider the LOCATION and CONTEXT of the business.

Return ONLY valid JSON:
{{
  "segments": [
    {{
      "segment": "College Students (18-22)",
      "display_name": "College Students",
      "age_range": "18-22",
      "count": <number of agents for this segment, must sum to {agent_count}>,
      "natural_prevalence": <percentage 1-100>,
      "budget_sensitivity": <0.0-1.0, how price-sensitive>,
      "influence_score": <0.0-1.0, how much they influence others>,
      "decision_speed": "fast|medium|slow",
      "personality_traits": ["social-media-active", "budget-conscious", "trend-following"],
      "main_motivation": "Why they'd try this specific product",
      "main_objection": "Their specific concern about this product",
      "trigger_to_adopt": "What makes them sign up/buy",
      "trigger_to_churn": "What makes them leave/stop buying",
      "real_world_context": "Brief description of their daily life relevant to this product"
    }}
  ]
}}

RULES:
- Segment names must be plain English that anyone can understand
- Include age ranges where relevant
- Consider the actual location and demographics
- Count must sum to exactly {agent_count}
- Be specific to THIS business, not generic
- Include at least 2 segments that would be skeptical or unlikely to adopt
"""
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model_tier1,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        segments = result.get("segments", [])

        if not segments:
            return _get_default_segments(agent_count)

        total = sum(s.get("count", 0) for s in segments)
        if total != agent_count:
            _adjust_counts(segments, agent_count)

        return segments
    except Exception:
        return _get_default_segments(agent_count)


def _adjust_counts(segments: list, target: int):
    total = sum(s.get("count", 0) for s in segments)
    if total == 0:
        per_segment = target // len(segments)
        for s in segments:
            s["count"] = per_segment
        segments[-1]["count"] += target - (per_segment * len(segments))
        return

    diff = target - total
    if diff != 0:
        segments[-1]["count"] = max(1, segments[-1].get("count", 0) + diff)


def _instantiate_persona(base: dict, index: int) -> dict:
    first_names = [
        "Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew",
        "Quinn", "Avery", "Blake", "Cameron", "Dana", "Emery", "Finley",
        "Harper", "Jamie", "Kelly", "Logan", "Peyton", "Reese", "Skyler",
        "Rowan", "Sage", "Kai", "Nico", "Ezra", "Mira", "Zara", "Arin",
    ]
    segment_key = base.get("segment", "customer").lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")

    return {
        "name": f"{random.choice(first_names)}_{segment_key}_{index}",
        "segment": base.get("segment", "General Customer"),
        "personality": base.get("personality_traits", []),
        "budget_sensitivity": base.get("budget_sensitivity", 0.5),
        "influence_score": max(0.0, min(1.0, base.get("influence_score", 0.3) + random.uniform(-0.1, 0.1))),
        "decision_speed": base.get("decision_speed", "medium"),
        "main_motivation": base.get("main_motivation", ""),
        "main_objection": base.get("main_objection", ""),
        "trigger_to_adopt": base.get("trigger_to_adopt", ""),
        "trigger_to_churn": base.get("trigger_to_churn", ""),
        "real_world_context": base.get("real_world_context", ""),
        "memory": [],
        "status": "prospect",
    }


def _get_default_segments(agent_count: int) -> list:
    base = agent_count // 6
    remainder = agent_count - (base * 6)
    return [
        {"segment": "Young Professionals (25-35)", "count": base + remainder, "natural_prevalence": 25,
         "budget_sensitivity": 0.4, "influence_score": 0.6, "decision_speed": "medium",
         "personality_traits": ["career-focused", "tech-savvy", "social-media-active"]},
        {"segment": "College Students (18-24)", "count": base, "natural_prevalence": 20,
         "budget_sensitivity": 0.8, "influence_score": 0.5, "decision_speed": "fast",
         "personality_traits": ["budget-conscious", "trend-following", "peer-influenced"]},
        {"segment": "Working Parents (35-50)", "count": base, "natural_prevalence": 20,
         "budget_sensitivity": 0.5, "influence_score": 0.4, "decision_speed": "medium",
         "personality_traits": ["time-constrained", "value-oriented", "practical"]},
        {"segment": "Retirees (60+)", "count": base, "natural_prevalence": 10,
         "budget_sensitivity": 0.6, "influence_score": 0.3, "decision_speed": "slow",
         "personality_traits": ["routine-oriented", "quality-focused", "word-of-mouth"]},
        {"segment": "Local Business Owners", "count": base, "natural_prevalence": 10,
         "budget_sensitivity": 0.3, "influence_score": 0.7, "decision_speed": "medium",
         "personality_traits": ["networking", "ROI-focused", "community-connected"]},
        {"segment": "Bargain Hunters", "count": base, "natural_prevalence": 15,
         "budget_sensitivity": 0.95, "influence_score": 0.2, "decision_speed": "fast",
         "personality_traits": ["deal-seeking", "comparison-shopping", "low-loyalty"]},
    ]

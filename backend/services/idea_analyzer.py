"""
Analyzes a raw user idea and extracts structured simulation fields using LLM.
Generates follow-up questions when the idea is too vague.
"""
import json
from openai import AsyncOpenAI
from core.config import settings

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

VALID_VERTICALS = ["saas", "consumer_app", "marketplace", "physical_product", "service_business", "enterprise"]
VALID_PRICING_MODELS = ["freemium", "subscription", "one-time", "usage", "hybrid"]


async def analyze_idea(raw_idea: str) -> dict:
    prompt = f"""You are an expert business analyst. A user described an idea in their own words.
Your job is to extract structured business simulation parameters from it.

USER'S IDEA:
\"\"\"{raw_idea}\"\"\"

Extract the following fields. Infer reasonable values when the user didn't specify them explicitly.
Be creative but realistic. The user may have no business knowledge, so fill in smart defaults.

Return ONLY valid JSON with this exact structure:
{{
  "business_name": "A short catchy name for this business (infer from the idea)",
  "idea_description": "A clear 2-3 sentence description of what this product/service does",
  "vertical": "one of: saas, consumer_app, marketplace, physical_product, service_business, enterprise",
  "target_market": "A detailed description of who would use this (demographics, needs, behaviors)",
  "pricing_model": "one of: freemium, subscription, one-time, usage, hybrid",
  "currency": "The local currency symbol based on the country (e.g. ₹ for India, $ for USA, € for Europe, £ for UK)",
  "price_points": {{"tier_name": numeric_value, ...}},
  "gtm_channels": ["list", "of", "go-to-market", "channels"],
  "competitors": [
    {{"name": "Competitor Name", "url": "", "description": "What they do"}}
  ],
  "key_assumptions": [
    {{"variable": "churn_rate_monthly", "value": "5%"}},
    {{"variable": "word_of_mouth_rate", "value": "10%"}},
    {{"variable": "trial_to_paid_conversion", "value": "15%"}}
  ],
  "confidence": "high or low - high if you have enough info, low if the idea is too vague",
  "follow_up_questions": ["Only include 2-3 simple plain-language questions if confidence is low, otherwise empty list"]
}}

IMPORTANT RULES:
- vertical MUST be exactly one of: saas, consumer_app, marketplace, physical_product, service_business, enterprise
- pricing_model MUST be exactly one of: freemium, subscription, one-time, usage, hybrid
- CURRENCY: Detect the country from the idea. Use local currency and realistic local prices.
  For India use ₹ with prices like 150, 250, 500. For USA use $ with prices like 5, 15, 30.
  For UK use £, for Europe use €, etc. Default to $ if no country is mentioned.
- price_points must have at least one entry with numeric values IN THE LOCAL CURRENCY
- gtm_channels must have at least one entry
- competitors should be REAL competitors in that specific location/market if possible
- If the idea is clear enough, set confidence to "high" and leave follow_up_questions empty
- If the idea is vague, set confidence to "low" and ask 2-3 simple questions anyone could answer
- Questions should be in plain language, no jargon (e.g., "Who would use this?" not "Define your TAM")
- Always return valid JSON, nothing else
"""
    response = await client.chat.completions.create(
        model=settings.llm_model_tier1,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    result = _validate_and_fix(result)
    return result


async def refine_idea(raw_idea: str, answers: list[dict]) -> dict:
    qa_context = "\n".join(
        f"Q: {a['question']}\nA: {a['answer']}" for a in answers
    )

    prompt = f"""You are an expert business analyst. A user described an idea and answered follow-up questions.
Now produce the final structured simulation parameters.

ORIGINAL IDEA:
\"\"\"{raw_idea}\"\"\"

FOLLOW-UP Q&A:
{qa_context}

Return ONLY valid JSON with this exact structure:
{{
  "business_name": "A short catchy name for this business",
  "idea_description": "A clear 2-3 sentence description of what this product/service does",
  "vertical": "one of: saas, consumer_app, marketplace, physical_product, service_business, enterprise",
  "target_market": "A detailed description of who would use this",
  "pricing_model": "one of: freemium, subscription, one-time, usage, hybrid",
  "currency": "The local currency symbol (₹, $, €, £, etc.)",
  "price_points": {{"tier_name": numeric_value, ...}},
  "gtm_channels": ["list", "of", "go-to-market", "channels"],
  "competitors": [
    {{"name": "Competitor Name", "url": "", "description": "What they do"}}
  ],
  "key_assumptions": [
    {{"variable": "churn_rate_monthly", "value": "5%"}},
    {{"variable": "word_of_mouth_rate", "value": "10%"}},
    {{"variable": "trial_to_paid_conversion", "value": "15%"}}
  ]
}}

IMPORTANT RULES:
- vertical MUST be exactly one of: saas, consumer_app, marketplace, physical_product, service_business, enterprise
- pricing_model MUST be exactly one of: freemium, subscription, one-time, usage, hybrid
- CURRENCY: Detect the country from the idea and answers. Use local currency with realistic local prices.
- price_points must have at least one entry with numeric values IN LOCAL CURRENCY
- gtm_channels must have at least one entry
- competitors should be REAL competitors in the specific location if possible
- Always return valid JSON, nothing else
"""
    response = await client.chat.completions.create(
        model=settings.llm_model_tier1,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    result = _validate_and_fix(result)
    return result


def _normalize_vertical(raw: str | None) -> str:
    if not raw:
        return "saas"
    v = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    if v in VALID_VERTICALS:
        return v
    return "saas"


def _normalize_pricing_model(raw: str | None) -> str:
    if not raw:
        return "freemium"
    p = str(raw).strip().lower().replace("_", "-")
    p = p.replace("one time", "one-time").replace("onetime", "one-time")
    if p in VALID_PRICING_MODELS:
        return p
    return "freemium"


def _safe_price_float(v) -> float:
    """Coerce LLM output (numbers, '$10', '₹150') to float without crashing."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = str(v).strip().replace(",", "")
    for sym in ("$", "€", "£", "₹", "¥"):
        s = s.replace(sym, "")
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _validate_and_fix(data: dict) -> dict:
    data["vertical"] = _normalize_vertical(data.get("vertical"))

    data["pricing_model"] = _normalize_pricing_model(data.get("pricing_model"))

    if not data.get("currency"):
        data["currency"] = "$"

    if not data.get("price_points") or not isinstance(data["price_points"], dict):
        data["price_points"] = {"free": 0, "basic": 29, "pro": 99}
    data["price_points"] = {str(k): _safe_price_float(v) for k, v in data["price_points"].items()}

    if not data.get("gtm_channels") or not isinstance(data["gtm_channels"], list):
        data["gtm_channels"] = ["social_media", "content_marketing"]

    if not data.get("competitors") or not isinstance(data["competitors"], list):
        data["competitors"] = []
    fixed_competitors = []
    for c in data["competitors"]:
        if isinstance(c, str) and c.strip():
            fixed_competitors.append({"name": c.strip(), "url": "", "description": ""})
        elif isinstance(c, dict):
            fixed_competitors.append(
                {
                    "name": str(c.get("name") or "").strip() or "Unknown",
                    "url": str(c.get("url") or ""),
                    "description": str(c.get("description") or ""),
                }
            )
    data["competitors"] = fixed_competitors

    if not data.get("key_assumptions") or not isinstance(data["key_assumptions"], list):
        data["key_assumptions"] = [
            {"variable": "churn_rate_monthly", "value": "5%"},
            {"variable": "word_of_mouth_rate", "value": "10%"},
            {"variable": "trial_to_paid_conversion", "value": "15%"},
        ]
    else:
        fixed_assumptions = []
        for a in data["key_assumptions"]:
            if isinstance(a, dict):
                fixed_assumptions.append(
                    {
                        "variable": str(a.get("variable") or ""),
                        "value": "" if a.get("value") is None else str(a.get("value")),
                    }
                )
        if fixed_assumptions:
            data["key_assumptions"] = fixed_assumptions

    return data

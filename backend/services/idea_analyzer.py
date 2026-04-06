"""
Analyzes a raw user idea and extracts structured simulation fields using LLM.
Generates follow-up questions when the idea is too vague.
"""
import asyncio
import json
import re

from core.config import settings
from services.llm_router import AllProvidersExhausted, call_llm
from services.llm_text_json import coerce_llm_json_text

VALID_VERTICALS = ["saas", "consumer_app", "marketplace", "physical_product", "service_business", "enterprise"]
VALID_PRICING_MODELS = ["freemium", "subscription", "one-time", "usage", "hybrid"]


def _currency_from_text(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["india", "indian", "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "hyderabad"]):
        return "₹"
    if any(x in t for x in ["uk", "united kingdom", "london", "england", "britain"]):
        return "£"
    if any(x in t for x in ["europe", "european", "germany", "france", "spain", "italy", "netherlands"]):
        return "€"
    return "$"


def _guess_vertical(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["app", "mobile", "social", "community"]):
        return "consumer_app"
    if any(x in t for x in ["marketplace", "buy and sell", "seller", "vendor"]):
        return "marketplace"
    if any(x in t for x in ["subscription", "saas", "software", "tool", "dashboard", "automation"]):
        return "saas"
    if any(x in t for x in ["service", "agency", "consulting", "studio"]):
        return "service_business"
    if any(x in t for x in ["hardware", "device", "physical", "product"]):
        return "physical_product"
    return "saas"


def _fallback_analysis(raw_idea: str, *, include_questions: bool) -> dict:
    cleaned = " ".join(raw_idea.strip().split())
    if not cleaned:
        cleaned = "New business idea"
    words = re.findall(r"[A-Za-z0-9']+", cleaned)
    short_name = " ".join(words[:4]).strip().title() if words else "New Venture"
    if len(short_name) < 3:
        short_name = "New Venture"

    vertical = _guess_vertical(cleaned)
    currency = _currency_from_text(cleaned)

    if currency == "₹":
        price_points = {"starter": 149, "growth": 399}
    elif currency == "€":
        price_points = {"starter": 9, "growth": 29}
    elif currency == "£":
        price_points = {"starter": 8, "growth": 24}
    else:
        price_points = {"starter": 9, "growth": 29}

    out = {
        "business_name": short_name,
        "idea_description": (
            f"{cleaned}. This concept is framed as a practical early-stage business "
            "that can be tested quickly with a lightweight first launch."
        ),
        "vertical": vertical,
        "target_market": "Early adopters in local and online communities who need this outcome now.",
        "pricing_model": "freemium",
        "currency": currency,
        "price_points": price_points,
        "gtm_channels": ["social_media", "community_outreach", "local_partnerships"],
        "competitors": [],
        "key_assumptions": [
            {"variable": "churn_rate_monthly", "value": "7%"},
            {"variable": "word_of_mouth_rate", "value": "12%"},
            {"variable": "trial_to_paid_conversion", "value": "10%"},
        ],
    }
    if include_questions:
        out["confidence"] = "low"
        out["follow_up_questions"] = [
            "Who is your first target customer group?",
            "How would you like to make money from this idea?",
            "What is the main problem this solves better than current options?",
        ]
    return out


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
    try:
        content = await asyncio.wait_for(
            call_llm(
                messages=[{"role": "user", "content": prompt}],
                agent_tier=1,
                max_tokens=1200,
                temperature=0.3,
                json_mode=True,
                read_timeout=settings.idea_analysis_llm_read_timeout_seconds,
                max_provider_attempts=settings.idea_analysis_max_provider_attempts,
            ),
            timeout=settings.idea_analysis_total_deadline_seconds,
        )
        result = json.loads(coerce_llm_json_text(content))
        result = _validate_and_fix(result)
        return result
    except (AllProvidersExhausted, asyncio.TimeoutError):
        # Non-blocking fallback so users can still progress through the wizard.
        return _fallback_analysis(raw_idea, include_questions=True)


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
    try:
        content = await asyncio.wait_for(
            call_llm(
                messages=[{"role": "user", "content": prompt}],
                agent_tier=1,
                max_tokens=1200,
                temperature=0.3,
                json_mode=True,
                read_timeout=settings.idea_analysis_llm_read_timeout_seconds,
                max_provider_attempts=settings.idea_analysis_max_provider_attempts,
            ),
            timeout=settings.idea_analysis_total_deadline_seconds,
        )
        result = json.loads(coerce_llm_json_text(content))
        result = _validate_and_fix(result)
        return result
    except (AllProvidersExhausted, asyncio.TimeoutError):
        joined_answers = " ".join(str(a.get("answer") or "") for a in answers if isinstance(a, dict)).strip()
        merged = raw_idea if not joined_answers else f"{raw_idea}. {joined_answers}"
        return _fallback_analysis(merged, include_questions=False)


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

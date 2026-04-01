"""
Multi-provider LLM router with per-key rate tracking, rotation, and graceful fallback.

Provider priority:
  Tier 1 (quality): DigitalOcean Gradient (if MODEL_ACCESS_KEY set) → Groq 70b → Gemini → OpenRouter
  Tier 2 (volume):  DO tier-2 model → Groq 8b → Groq 70b → Gemini

Never exposes raw API keys in logs — only key_0, key_1, etc.
"""
import json
import random
import time
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()

# Per-provider HTTP timeouts. Keep total wall time under ~90s so gateways (e.g. DO App Platform ~100s) return JSON, not 504.
HTTPX_CONNECT = 15.0
HTTPX_WRITE = 45.0
HTTPX_POOL = 10.0
LLM_DEFAULT_READ_TIMEOUT = 55.0


# ── Exceptions ────────────────────────────────────────────────────────────────

class CrowdAgentSkip(Exception):
    """Raised for Tier 3 agents — no LLM call, use crowd_agent_decision()."""


class AllProvidersExhausted(Exception):
    """All providers and keys are depleted for this tier."""


# ── Key tracking ──────────────────────────────────────────────────────────────

class ApiKey:
    def __init__(self, index: int, value: str):
        self.index = index
        self.value = value
        self.requests_today: int = 0
        self.requests_this_minute: int = 0
        self._last_minute_reset: float = time.monotonic()
        self._cooling_until: float = 0.0

    def is_cooling(self) -> bool:
        return time.monotonic() < self._cooling_until

    def _tick_minute(self) -> None:
        now = time.monotonic()
        if now - self._last_minute_reset >= 60.0:
            self.requests_this_minute = 0
            self._last_minute_reset = now

    def can_use(self, rpm_limit: int, rpd_limit: int) -> bool:
        if self.is_cooling():
            return False
        self._tick_minute()
        return self.requests_this_minute < rpm_limit and self.requests_today < rpd_limit

    def record(self) -> None:
        self._tick_minute()
        self.requests_this_minute += 1
        self.requests_today += 1

    def cool_down(self, seconds: float) -> None:
        self._cooling_until = time.monotonic() + max(seconds, 5.0)

    @property
    def label(self) -> str:
        return f"key_{self.index}"


# ── Provider ──────────────────────────────────────────────────────────────────

class Provider:
    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        api_keys: list[ApiKey],
        rpm_limit: int,
        rpd_limit: int,
    ):
        self.name = name
        self.base_url = base_url
        self.model = model
        self.api_keys = api_keys
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit

    def is_available(self) -> bool:
        return any(k.can_use(self.rpm_limit, self.rpd_limit) for k in self.api_keys)

    def next_key(self) -> Optional[ApiKey]:
        for key in self.api_keys:
            if key.can_use(self.rpm_limit, self.rpd_limit):
                return key
        return None

    def status(self) -> dict:
        return {
            "name": self.name,
            "model": self.model,
            "available": self.is_available(),
            "keys": [
                {
                    "label": k.label,
                    "requests_today": k.requests_today,
                    "requests_this_minute": k.requests_this_minute,
                    "cooling": k.is_cooling(),
                }
                for k in self.api_keys
            ],
        }


# ── Provider chains (built lazily on first call) ──────────────────────────────

_tier1_chain: list[Provider] = []
_tier2_chain: list[Provider] = []
_built = False


def _build_chains() -> None:
    global _tier1_chain, _tier2_chain, _built
    if _built:
        return

    from core.config import settings

    raw_groq = settings.groq_api_keys or ""
    groq_values = [k.strip() for k in raw_groq.split(",") if k.strip()]

    # Also include the legacy LLM_API_KEY if it looks like a Groq key (gsk_)
    legacy = (settings.llm_api_key or "").strip()
    if legacy.startswith("gsk_") and legacy not in groq_values:
        groq_values.append(legacy)

    if not groq_values:
        logger.warning("no_groq_keys_configured")

    # Each provider gets independent ApiKey instances (separate counters)
    def groq_keys() -> list[ApiKey]:
        return [ApiKey(i, v) for i, v in enumerate(groq_values)]

    gemini_keys = (
        [ApiKey(0, settings.gemini_api_key)] if settings.gemini_api_key else []
    )
    openrouter_keys = (
        [ApiKey(0, settings.openrouter_api_key)] if settings.openrouter_api_key else []
    )

    groq_70b = Provider(
        name="groq_70b",
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        api_keys=groq_keys(),
        rpm_limit=30,
        rpd_limit=1000,
    )
    groq_8b = Provider(
        name="groq_8b",
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.1-8b-instant",
        api_keys=groq_keys(),
        rpm_limit=30,
        rpd_limit=14400,
    )
    gemini = Provider(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        model="gemini-2.0-flash",
        api_keys=gemini_keys,
        rpm_limit=15,
        rpd_limit=1500,
    )
    openrouter = Provider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        model="meta-llama/llama-3.3-70b-instruct:free",
        api_keys=openrouter_keys,
        rpm_limit=20,
        rpd_limit=200,
    )

    do_key = (settings.digitalocean_model_access_key or "").strip()
    do_tier1_list: list[Provider] = []
    do_tier2_list: list[Provider] = []
    if do_key:
        do_base = settings.digitalocean_inference_base_url.rstrip("/")
        m1 = (settings.llm_model_tier1 or "alibaba-qwen3-32b").strip()
        m2 = (settings.llm_model_tier2 or m1).strip()
        # Generous limits; DO bills per token — adjust if you hit HTTP 429s
        do_tier1_list.append(
            Provider(
                name="digitalocean_tier1",
                base_url=do_base,
                model=m1,
                api_keys=[ApiKey(0, do_key)],
                rpm_limit=120,
                rpd_limit=100_000,
            )
        )
        do_tier2_list.append(
            Provider(
                name="digitalocean_tier2",
                base_url=do_base,
                model=m2,
                api_keys=[ApiKey(0, do_key)],
                rpm_limit=120,
                rpd_limit=100_000,
            )
        )
        logger.info(
            "llm_router_digitalocean_enabled",
            base_url=do_base,
            tier1_model=m1,
            tier2_model=m2,
        )

    # Tier 1: best quality (DO first when configured)
    _tier1_chain = do_tier1_list + [groq_70b, gemini, openrouter]
    # Tier 2: high volume
    _tier2_chain = do_tier2_list + [groq_8b, groq_70b, gemini]
    _built = True


def get_providers() -> list[dict]:
    """Return status for all unique providers (for admin endpoint)."""
    _build_chains()
    seen: set[str] = set()
    result = []
    for chain in [_tier1_chain, _tier2_chain]:
        for p in chain:
            if p.name not in seen:
                seen.add(p.name)
                result.append(p.status())
    return result


# ── Core HTTP call ────────────────────────────────────────────────────────────


def _extract_assistant_text(data: dict) -> str | None:
    """
    Normalize OpenAI-compatible chat completion payloads.
    Some hosts (e.g. DigitalOcean / multi-modal adapters) return content as a list of parts
    or omit string content when using alternate fields.
    """
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    ch0 = choices[0]
    if not isinstance(ch0, dict):
        return None
    msg = ch0.get("message")
    if not isinstance(msg, dict):
        msg = {}

    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text" and part.get("text"):
                parts.append(str(part["text"]))
            elif isinstance(part.get("text"), str):
                parts.append(part["text"])
        joined = "".join(parts).strip()
        if joined:
            return joined

    for key in ("refusal", "reasoning"):
        val = msg.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    legacy = ch0.get("text")
    if isinstance(legacy, str) and legacy.strip():
        return legacy.strip()

    return None


def _use_openai_json_response_format(provider: Provider) -> bool:
    """
    response_format: {type: json_object} is OpenAI-specific. DigitalOcean-hosted models
    (Qwen, Llama, etc.) often return HTTP 500 when this field is sent — rely on prompt-only JSON instead.
    """
    return not provider.name.startswith("digitalocean")


async def _call_provider(
    provider: Provider,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    json_mode: bool,
    read_timeout: float = LLM_DEFAULT_READ_TIMEOUT,
) -> str:
    key = provider.next_key()
    if key is None:
        raise AllProvidersExhausted(f"{provider.name}: no available keys")

    key.record()

    # DigitalOcean serverless inference: prefer max_completion_tokens; max_tokens is deprecated there.
    # Groq / OpenRouter / Gemini OpenAI-compat: use max_tokens.
    body: dict = {
        "model": provider.model,
        "messages": messages,
        "temperature": temperature,
    }
    if provider.name.startswith("digitalocean"):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens

    if json_mode and _use_openai_json_response_format(provider):
        body["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {key.value}",
        "Content-Type": "application/json",
    }

    timeout = httpx.Timeout(
        connect=HTTPX_CONNECT,
        read=read_timeout,
        write=HTTPX_WRITE,
        pool=HTTPX_POOL,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as http:
            resp = await http.post(
                f"{provider.base_url}/chat/completions",
                json=body,
                headers=headers,
            )

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("retry-after", "60"))
            key.cool_down(retry_after)
            logger.warning(
                "llm_rate_limited",
                provider=provider.name,
                key=key.label,
                retry_after=retry_after,
            )
            raise AllProvidersExhausted(f"{provider.name} {key.label} rate limited")

        if not resp.is_success:
            logger.warning(
                "llm_provider_http_error",
                provider=provider.name,
                key=key.label,
                status=resp.status_code,
                body=resp.text[:400],
            )
            raise AllProvidersExhausted(f"{provider.name} HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        content = _extract_assistant_text(data)
        if content is None:
            logger.warning(
                "llm_empty_content_shape",
                provider=provider.name,
                key=key.label,
                sample=str(data)[:500],
            )
            raise AllProvidersExhausted(
                f"{provider.name}: empty or missing message.content in response"
            )
        logger.info(
            "llm_call_ok",
            provider=provider.name,
            model=provider.model,
            key=key.label,
        )
        return content

    except AllProvidersExhausted:
        raise
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.warning("llm_provider_error", provider=provider.name, error=str(exc))
        raise AllProvidersExhausted(f"{provider.name} connection error") from exc
    except Exception as exc:
        logger.warning("llm_provider_unexpected", provider=provider.name, error=str(exc))
        raise AllProvidersExhausted(f"{provider.name} unexpected: {exc}") from exc


# ── Public call_llm ───────────────────────────────────────────────────────────

async def call_llm(
    messages: list[dict],
    agent_tier: int,
    temperature: float = 0.7,
    max_tokens: int = 300,
    json_mode: bool = False,
    *,
    read_timeout: float | None = None,
    max_provider_attempts: int | None = None,
) -> str:
    """
    Route an LLM call through the appropriate provider chain.

    agent_tier=1  → Groq 70b → Gemini → OpenRouter  (best quality)
    agent_tier=2  → Groq 8b  → Groq 70b → Gemini    (high volume)
    agent_tier=3  → raises CrowdAgentSkip immediately (no API call)

    max_provider_attempts limits how many providers are tried (stays under HTTP gateway timeouts).
    read_timeout sets per-request read seconds (default LLM_DEFAULT_READ_TIMEOUT).
    """
    if agent_tier == 3:
        raise CrowdAgentSkip("Tier 3 agents use probabilistic logic")

    _build_chains()
    chain = _tier1_chain if agent_tier == 1 else _tier2_chain
    rt = read_timeout if read_timeout is not None else LLM_DEFAULT_READ_TIMEOUT
    attempts = 0
    last_failure: str | None = None

    for provider in chain:
        if not provider.is_available():
            logger.info("llm_provider_skipped", provider=provider.name, reason="unavailable")
            continue
        if max_provider_attempts is not None and attempts >= max_provider_attempts:
            break
        attempts += 1
        try:
            return await _call_provider(
                provider, messages, temperature, max_tokens, json_mode, read_timeout=rt
            )
        except AllProvidersExhausted as exc:
            last_failure = str(exc)
            continue
        except Exception as exc:
            logger.warning("llm_provider_unexpected", provider=provider.name, error=str(exc))
            last_failure = str(exc)
            continue

    raise AllProvidersExhausted(
        last_failure
        or "All LLM providers failed. Check DigitalOcean inference (model id, key) or add GROQ_API_KEYS as fallback."
    )


# ── Probabilistic crowd agent decision ───────────────────────────────────────

_SEGMENT_PROFILES: dict[str, dict] = {
    # keyword → {adopt, reject, defer, refer}
    "tech":         {"adopt": 0.45, "reject": 0.15, "defer": 0.30, "refer": 0.20},
    "engineer":     {"adopt": 0.45, "reject": 0.15, "defer": 0.30, "refer": 0.20},
    "developer":    {"adopt": 0.45, "reject": 0.15, "defer": 0.30, "refer": 0.20},
    "early":        {"adopt": 0.40, "reject": 0.20, "defer": 0.25, "refer": 0.18},
    "enthusiast":   {"adopt": 0.40, "reject": 0.20, "defer": 0.25, "refer": 0.18},
    "student":      {"adopt": 0.25, "reject": 0.40, "defer": 0.30, "refer": 0.10},
    "college":      {"adopt": 0.25, "reject": 0.40, "defer": 0.30, "refer": 0.10},
    "budget":       {"adopt": 0.18, "reject": 0.50, "defer": 0.28, "refer": 0.06},
    "bargain":      {"adopt": 0.18, "reject": 0.50, "defer": 0.28, "refer": 0.06},
    "price":        {"adopt": 0.20, "reject": 0.45, "defer": 0.30, "refer": 0.08},
    "skeptic":      {"adopt": 0.10, "reject": 0.58, "defer": 0.28, "refer": 0.04},
    "reluctant":    {"adopt": 0.12, "reject": 0.55, "defer": 0.28, "refer": 0.05},
    "conservative": {"adopt": 0.12, "reject": 0.55, "defer": 0.28, "refer": 0.05},
    "senior":       {"adopt": 0.15, "reject": 0.45, "defer": 0.35, "refer": 0.06},
    "elder":        {"adopt": 0.12, "reject": 0.48, "defer": 0.35, "refer": 0.05},
    "retire":       {"adopt": 0.12, "reject": 0.48, "defer": 0.35, "refer": 0.05},
    "influencer":   {"adopt": 0.50, "reject": 0.15, "defer": 0.20, "refer": 0.42},
    "creator":      {"adopt": 0.48, "reject": 0.18, "defer": 0.20, "refer": 0.35},
    "blogger":      {"adopt": 0.45, "reject": 0.18, "defer": 0.22, "refer": 0.30},
    "power":        {"adopt": 0.45, "reject": 0.20, "defer": 0.25, "refer": 0.25},
    "expert":       {"adopt": 0.42, "reject": 0.22, "defer": 0.25, "refer": 0.22},
    "enterprise":   {"adopt": 0.15, "reject": 0.42, "defer": 0.38, "refer": 0.08},
    "corporate":    {"adopt": 0.15, "reject": 0.42, "defer": 0.38, "refer": 0.08},
    "smb":          {"adopt": 0.25, "reject": 0.35, "defer": 0.35, "refer": 0.12},
    "owner":        {"adopt": 0.28, "reject": 0.32, "defer": 0.35, "refer": 0.14},
    "parent":       {"adopt": 0.30, "reject": 0.30, "defer": 0.35, "refer": 0.12},
    "mom":          {"adopt": 0.32, "reject": 0.28, "defer": 0.35, "refer": 0.14},
    "dad":          {"adopt": 0.28, "reject": 0.32, "defer": 0.35, "refer": 0.12},
    "professional": {"adopt": 0.35, "reject": 0.28, "defer": 0.32, "refer": 0.16},
    "worker":       {"adopt": 0.30, "reject": 0.32, "defer": 0.33, "refer": 0.12},
}

_DEFAULT_PROFILE = {"adopt": 0.25, "reject": 0.35, "defer": 0.35, "refer": 0.10}

_DESCRIPTIONS: dict[str, list[str]] = {
    "adopted": [
        "Signed up after seeing the value proposition. Ready to get started.",
        "Decided to try it — the benefits outweighed the initial hesitation.",
        "Word of mouth was the tipping point. Signed up without looking back.",
        "The pricing felt right for the value offered. Converted to customer.",
        "Tried the free tier and immediately saw enough value to commit.",
    ],
    "rejected": [
        "Not convinced enough at this stage. Moved on to other options.",
        "The price point was a dealbreaker. Chose to pass for now.",
        "Had specific concerns about fit that weren't addressed. Declined.",
        "Compared with alternatives and chose a competitor's solution.",
        "Not ready to commit — will revisit only if something changes.",
    ],
    "deferred": [
        "Interested but not ready to decide yet. Still evaluating options.",
        "Put the decision off — too busy with other priorities right now.",
        "Wants to see more social proof before committing. Still on the fence.",
        "Waiting for a trusted friend's recommendation before signing up.",
        "Bookmarked it to revisit next month. Decision is delayed.",
    ],
    "referred": [
        "Loved it so much they recommended it to two colleagues immediately.",
        "Became a spontaneous advocate — shared it on their social channels.",
        "Brought it up in a team meeting. Generated genuine word-of-mouth.",
        "Recommended to a friend dealing with the same problem. High intent.",
        "Left an unsolicited positive review and tagged the brand.",
    ],
    "churned": [
        "Cancelled after not seeing enough value in the first billing period.",
        "A price increase was the tipping point — switched to a competitor.",
        "The product didn't solve their core problem the way they expected.",
        "Lost interest after the initial excitement wore off. Disengaged.",
        "Found a cheaper alternative that met their needs well enough.",
    ],
}


def crowd_agent_decision(
    segment: str,
    turn: int,
    current_adoption_rate: float,
    price_sensitivity: str = "medium",
) -> dict:
    """
    Pure-Python probabilistic agent decision — zero LLM calls.
    Returns: {event_type, event_description, is_probabilistic: True}
    """
    seg_lower = segment.lower()
    profile = _DEFAULT_PROFILE.copy()
    for keyword, prof in _SEGMENT_PROFILES.items():
        if keyword in seg_lower:
            profile = prof.copy()
            break

    # Social proof: higher adoption rate boosts adopt probability
    social_boost = min(0.30, current_adoption_rate * 0.40)
    adopt = min(0.90, profile["adopt"] + social_boost)

    # After turn 25, fence-sitters finally decide (halve defer probability)
    defer = profile["defer"] * (0.50 if turn > 25 else 1.0)

    reject = profile["reject"]

    # Price sensitivity adjustment
    if price_sensitivity == "low":
        adopt = min(0.90, adopt * 1.25)
    elif price_sensitivity == "high":
        adopt = adopt * 0.70

    # Normalize to sum to 1
    total = adopt + reject + defer
    adopt /= total
    reject /= total

    roll = random.random()
    if roll < adopt:
        event_type = "referred" if random.random() < profile["refer"] else "adopted"
    elif roll < adopt + reject:
        event_type = "rejected"
    else:
        event_type = "deferred"

    return {
        "event_type": event_type,
        "event_description": random.choice(_DESCRIPTIONS.get(event_type, _DESCRIPTIONS["deferred"])),
        "is_probabilistic": True,
    }

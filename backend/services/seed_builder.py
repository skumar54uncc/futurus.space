"""
Converts wizard input into a MiroFish-compatible seed with real-world market context.
Includes location-specific knowledge, demographic data, and competitive landscape.
"""
import ipaddress
import json
import re
from urllib.parse import urlparse

import httpx

from schemas.simulation import SimulationCreateRequest
from services.llm_router import call_llm

# SECURITY: SSRF prevention for user-supplied competitor URLs
ALLOWED_SCHEMES = frozenset({"http", "https"})
BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "169.254.169.254",
        "metadata.google.internal",
        "100.100.100.200",
    }
)


def _is_safe_url(url: str) -> bool:
    # SECURITY: Only allow public HTTP(S) targets; block obvious internal endpoints
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        if host in BLOCKED_HOSTS:
            return False
        try:
            ip = ipaddress.ip_address(host)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


async def build_seed(request: SimulationCreateRequest) -> dict:
    competitor_context = await _enrich_competitors(
        [c.model_dump() for c in request.competitors]
    )
    market_context = await _generate_market_context(request, competitor_context)

    seed = {
        "world_description": market_context,
        "business": {
            "name": request.business_name,
            "description": request.idea_description,
            "pricing_model": request.pricing_model,
            "price_points": request.price_points,
            "gtm_channels": request.gtm_channels,
            "vertical": request.vertical,
        },
        "market": {
            "description": request.target_market,
            "competitors": competitor_context,
            "size_estimate": "medium",
        },
        "assumptions": {
            item.variable: item.value for item in request.key_assumptions
        },
        "simulation_config": {
            "time_unit": "week",
            "total_turns": request.max_turns,
            "agent_count": request.agent_count,
        },
    }
    return seed


async def _enrich_competitors(competitors: list) -> list:
    enriched = []
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client_http:
        for comp in competitors[:5]:
            entry = {
                "name": (comp.get("name") or "")[:200],
                "description": (comp.get("description") or "")[:500],
            }
            url = (comp.get("url") or "").strip()
            if url and _is_safe_url(url):
                try:
                    resp = await client_http.get(
                        url,
                        headers={"User-Agent": "Futurus/1.0 (+https://futurus.dev)"},
                    )
                    html = resp.text[:3000]
                    title_match = re.search(
                        r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE
                    )
                    if title_match:
                        entry["scraped_title"] = title_match.group(1).strip()[:200]
                except Exception:
                    pass
            enriched.append(entry)
    return enriched


async def _generate_market_context(
    request: SimulationCreateRequest, competitors: list
) -> str:
    prompt = f"""You are a market research analyst preparing a real-world market brief for a business simulation.
Your analysis should be grounded in real-world data and conditions.

Business: {request.business_name}
Idea: {request.idea_description}
Target market: {request.target_market}
Pricing: {request.pricing_model} at {json.dumps(request.price_points)}
GTM channels: {", ".join(request.gtm_channels)}
Competitors: {json.dumps([c["name"] for c in competitors])}

Write a detailed 4-paragraph market analysis:

Para 1: LOCAL MARKET REALITY — Describe the specific area/market this business targets.
Include realistic demographics, foot traffic patterns, local economy, and customer behavior
specific to this location. Reference real-world conditions (e.g., "Charlotte's Uptown area
sees 50,000+ daily office workers" or "college towns typically have 30% student population").

Para 2: CUSTOMER BEHAVIOR — How do real people in this market actually make purchasing decisions?
What are their daily routines, spending habits, and preferences? Include realistic price
sensitivity data (e.g., "average coffee spend for millennials is $4-6 per visit").

Para 3: COMPETITIVE LANDSCAPE — Who are the real competitors? What are typical margins,
switching costs, and market maturity? Include industry statistics where possible.

Para 4: SUCCESS FACTORS AND RISKS — What does it take to succeed here, based on real-world
data? What typically kills new entrants in this market? Include failure rate statistics
for this type of business if relevant.

Be SPECIFIC and REALISTIC. Use actual numbers and real-world data points wherever possible.
Write in present tense. No fluff.
"""
    return await call_llm(
        messages=[{"role": "user", "content": prompt}],
        agent_tier=1,
        max_tokens=1000,
        temperature=0.3,
    )

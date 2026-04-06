"""
Tavily-based web search for real industry citations.
Called before report generation to ground the LLM narrative in verified sources.
Returns [] gracefully if Tavily is not configured or all searches fail.
"""
import asyncio
import re
from urllib.parse import urlparse

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_TIMEOUT = 12.0
_MAX_CITATIONS = 8
_RESULTS_PER_QUERY = 4


async def _tavily_search(client: httpx.AsyncClient, query: str, *, simulation_mode: bool) -> list[dict]:
    depth = "basic" if simulation_mode else "advanced"
    try:
        resp = await client.post(
            _TAVILY_ENDPOINT,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "search_depth": depth,
                "include_answer": False,
                "max_results": _RESULTS_PER_QUERY,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as exc:
        logger.warning("tavily_search_failed", query=query[:80], error=str(exc))
        return []


def _extract_keywords(text: str, limit: int = 6) -> list[str]:
    if not text:
        return []
    stop = {
        "the", "and", "for", "with", "that", "this", "your", "from", "into", "about", "would",
        "could", "should", "their", "there", "have", "will", "into", "through", "across", "using",
    }
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t in stop or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= limit:
            break
    return out


def _build_queries(simulation) -> list[str]:
    vertical = (simulation.vertical or "").strip() or "startup"
    market = (simulation.target_market or "").strip()[:100]
    pricing = (simulation.pricing_model or "").strip() or "subscription"
    idea = (simulation.idea_description or "").strip()
    business = (simulation.business_name or "").strip()
    keywords = _extract_keywords(f"{business} {idea} {market}")
    kw = " ".join(keywords[:4])
    competitor_names: list[str] = []
    for c in (simulation.competitors or [])[:3]:
        if isinstance(c, dict):
            n = str(c.get("name") or "").strip()
            if n:
                competitor_names.append(n)
    comp = " vs ".join(competitor_names[:2])

    return [
        f"{business} {kw} {vertical} market size benchmark {market}",
        f"{kw} {vertical} user adoption churn benchmark {pricing} pricing",
        f"{kw} {market} customer behavior willingness to pay statistics",
        f"{kw} {vertical} competitors {comp} market share trends",
    ]


def _parse_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower()
        return domain[4:] if domain.startswith("www.") else domain
    except Exception:
        return url[:50]


def _extract_year(published_date: str | None) -> int | None:
    if not published_date:
        return None
    try:
        return int(str(published_date)[:4])
    except Exception:
        return None


def _relevance_score(result: dict, queries: list[str], simulation) -> int:
    title = (result.get("title") or "").lower()
    content = (result.get("content") or result.get("snippet") or "").lower()
    hay = f"{title} {content}"
    score = 0

    for q in queries:
        for tok in _extract_keywords(q, limit=8):
            if tok in hay:
                score += 2

    vertical = (simulation.vertical or "").replace("_", " ").lower()
    if vertical and vertical in hay:
        score += 5

    for tok in _extract_keywords((simulation.idea_description or "")[:240], limit=8):
        if tok in hay:
            score += 3

    src = _parse_domain((result.get("url") or "").strip())
    if src in {"reddit.com", "linkedin.com"}:
        score -= 3

    return score


async def fetch_industry_citations(simulation, *, simulation_mode: bool = True) -> list[dict]:
    """
    Fetch real industry citations for the simulation's business context via Tavily.
    Returns a list of dicts: {id, title, text, source, url, year}.
    Returns [] if TAVILY_API_KEY is not set or all queries fail.
    """
    if not settings.tavily_api_key:
        logger.info("tavily_not_configured_skipping_citations")
        return []

    queries = _build_queries(simulation)

    async with httpx.AsyncClient() as client:
        batches = await asyncio.gather(
            *[_tavily_search(client, q, simulation_mode=simulation_mode) for q in queries],
            return_exceptions=True,
        )

    all_results: list[dict] = []

    for batch in batches:
        if isinstance(batch, Exception):
            continue
        all_results.extend(batch)

    ranked = sorted(
        all_results,
        key=lambda r: _relevance_score(r, queries, simulation),
        reverse=True,
    )

    seen_urls: set[str] = set()
    citations: list[dict] = []
    for result in ranked:
        url = (result.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        content = (result.get("content") or result.get("snippet") or "").strip()
        if not content or len(content) < 40:
            continue

        rel = _relevance_score(result, queries, simulation)
        if rel < 4:
            continue

        seen_urls.add(url)
        citations.append(
            {
                "id": len(citations) + 1,
                "title": (result.get("title") or "").strip(),
                "text": content[:350],
                "source": _parse_domain(url),
                "url": url,
                "year": _extract_year(result.get("published_date")),
            }
        )
        if len(citations) >= _MAX_CITATIONS:
            break

    logger.info("citations_fetched", count=len(citations))
    return citations

"""
Tavily-based web search for real industry citations.
Called before report generation to ground the LLM narrative in verified sources.
Returns [] gracefully if Tavily is not configured or all searches fail.
"""
import asyncio
from urllib.parse import urlparse

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_TIMEOUT = 12.0
_MAX_CITATIONS = 8
_RESULTS_PER_QUERY = 3


async def _tavily_search(client: httpx.AsyncClient, query: str) -> list[dict]:
    try:
        resp = await client.post(
            _TAVILY_ENDPOINT,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "search_depth": "basic",
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


def _build_queries(simulation) -> list[str]:
    vertical = (simulation.vertical or "").strip()
    market = (simulation.target_market or "").strip()[:80]
    pricing = (simulation.pricing_model or "").strip()
    return [
        f"{vertical} startup failure rate industry statistics benchmark",
        f"{vertical} average customer churn rate benchmark {pricing}",
        f"{market} {vertical} market size trends statistics",
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


async def fetch_industry_citations(simulation) -> list[dict]:
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
            *[_tavily_search(client, q) for q in queries],
            return_exceptions=True,
        )

    seen_urls: set[str] = set()
    citations: list[dict] = []

    for batch in batches:
        if isinstance(batch, Exception):
            continue
        for result in batch:
            url = (result.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            content = (result.get("content") or result.get("snippet") or "").strip()
            if not content or len(content) < 40:
                continue

            seen_urls.add(url)
            citations.append({
                "id": len(citations) + 1,
                "title": (result.get("title") or "").strip(),
                "text": content[:350],
                "source": _parse_domain(url),
                "url": url,
                "year": _extract_year(result.get("published_date")),
            })

            if len(citations) >= _MAX_CITATIONS:
                break
        if len(citations) >= _MAX_CITATIONS:
            break

    logger.info("citations_fetched", count=len(citations))
    return citations

"""Regression: report narrative LLM failure must not poison the metrics-based verdict."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from services.report_generator import (
    _heuristic_viability_summary,
    _merge_viability_summary,
    _run_report_agent,
)


def _fake_simulation():
    return SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        business_name="Test Co",
        idea_description="A test idea",
        target_market="Test market",
        pricing_model="subscription",
        price_points={"basic": 10},
        gtm_channels=["organic"],
        competitors=[],
    )


@pytest.mark.asyncio
async def test_report_agent_llm_failure_keeps_heuristic_viability():
    """
    Bug 1 regression: when call_llm fails, merged viability must stay the metrics
    heuristic — not verdict_label=unclear / 'could not finish written analysis'.
    """
    metrics = {
        "summary": {
            "adoption_rate": 50.0,
            "churn_rate": 20.0,
            "viral_coefficient": 0.4,
            "total_adopters": 40,
        },
        "persona_breakdown": [],
    }
    validation = {"warning_flags": ["timesfm_high_divergence"], "composite_risk": "high"}
    heuristic = _heuristic_viability_summary(metrics["summary"])

    with patch(
        "services.report_generator.call_llm",
        new_callable=AsyncMock,
        side_effect=RuntimeError("All LLM providers failed"),
    ):
        qualitative = await _run_report_agent(
            _fake_simulation(), metrics, validation, events=[], citations=[]
        )

    merged = _merge_viability_summary(qualitative.get("viability_summary"), metrics["summary"])

    assert qualitative.get("narrative_source") == "heuristic"
    assert merged["verdict_label"] == heuristic["verdict_label"]
    assert merged["headline"] == heuristic["headline"]
    assert merged["verdict_label"] != "unclear"
    assert "could not finish" not in merged["headline"].lower()
    assert qualitative.get("key_insights") == []
    assert qualitative.get("risk_matrix") == []
    insights = qualitative.get("key_insights") or []
    assert not any("encountered an error" in (i.get("insight") or "").lower() for i in insights)

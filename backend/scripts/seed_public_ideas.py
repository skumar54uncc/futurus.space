"""Seed 12 trendy public ideas and backfill idea scores from reports.

Usage:
  python scripts/seed_public_ideas.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.database import AsyncSessionLocal, Base, engine
from models.published_idea import PublishedIdea
from models.simulation import Report, Simulation, SimulationStatus
from models.user import User
from services.idea_rating import compute_idea_scores, vertical_to_category


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


TREND_IDEAS: list[dict[str, Any]] = [
    {
        "business_name": "Tapas Madrid",
        "idea_description": "A social dining app that matches travelers and locals for curated small-plate nights in Madrid.",
        "target_market": "Urban millennials and digital nomads in Madrid seeking social food experiences.",
        "pricing_model": "commission",
        "vertical": "consumer_app",
        "summary_metrics": {
            "adoption_rate": 58.0,
            "churn_rate": 34.0,
            "viral_coefficient": 1.05,
            "confidence_score": 69.0,
            "total_adopters": 3120,
        },
        "key_insights": [
            {"insight": "Weekend cohorts showed stronger repeat behavior than weekday-only cohorts."},
            {"insight": "Retention improves when hosts publish menus at least 48 hours in advance."},
            {"insight": "Referral loops depend heavily on post-event photo sharing incentives."},
        ],
    },
    {
        "business_name": "AI Resume Tailor",
        "idea_description": "An AI copilot that rewrites resumes for each job posting and tracks interview response uplift.",
        "target_market": "Job seekers in tech, product, and marketing roles.",
        "pricing_model": "subscription",
        "vertical": "saas",
        "summary_metrics": {
            "adoption_rate": 72.0,
            "churn_rate": 18.0,
            "viral_coefficient": 1.18,
            "confidence_score": 81.0,
            "total_adopters": 4880,
        },
        "key_insights": [
            {"insight": "Users who import LinkedIn data convert 2.1x faster to paid plans."},
            {"insight": "One-click ATS scoring significantly increases weekly active usage."},
            {"insight": "Retention is highest when users receive interview callback analytics."},
        ],
    },
    {
        "business_name": "Creator Clip Studio",
        "idea_description": "Turn long videos into viral short clips with trend-aware caption and hook generation.",
        "target_market": "Independent creators and small media teams.",
        "pricing_model": "subscription",
        "vertical": "saas",
        "summary_metrics": {
            "adoption_rate": 67.0,
            "churn_rate": 22.0,
            "viral_coefficient": 1.42,
            "confidence_score": 77.0,
            "total_adopters": 4010,
        },
        "key_insights": [
            {"insight": "Templates tuned to platform trends drive the first-week aha moment."},
            {"insight": "Teams value collaboration workspaces more than extra rendering speed."},
            {"insight": "Viral lift peaks when creators publish within 2 hours of clip generation."},
        ],
    },
    {
        "business_name": "Voice Invoice Assistant",
        "idea_description": "Voice-to-invoice mobile assistant for freelancers that drafts, sends, and reminds clients.",
        "target_market": "Freelancers and solopreneurs in creative services.",
        "pricing_model": "subscription",
        "vertical": "service_business",
        "summary_metrics": {
            "adoption_rate": 61.0,
            "churn_rate": 20.0,
            "viral_coefficient": 0.82,
            "confidence_score": 84.0,
            "total_adopters": 2920,
        },
        "key_insights": [
            {"insight": "SMS payment nudges reduce outstanding invoices by over 25%."},
            {"insight": "Usage spikes around tax season and month-end closeouts."},
            {"insight": "High retention users rely on recurring invoice automation."},
        ],
    },
    {
        "business_name": "Neighborhood Skill Swap",
        "idea_description": "A local marketplace where neighbors trade time and expertise without cash.",
        "target_market": "Suburban communities and apartment complexes.",
        "pricing_model": "freemium",
        "vertical": "marketplace",
        "summary_metrics": {
            "adoption_rate": 54.0,
            "churn_rate": 28.0,
            "viral_coefficient": 1.24,
            "confidence_score": 65.0,
            "total_adopters": 2380,
        },
        "key_insights": [
            {"insight": "Early moderation standards are critical to trust and repeat exchanges."},
            {"insight": "Events and neighborhood challenges improve first transaction rate."},
            {"insight": "Referral incentives outperform paid local ads in this segment."},
        ],
    },
    {
        "business_name": "Green Carton Tracker",
        "idea_description": "SMB tool to track packaging footprint and suggest lower-cost sustainable alternatives.",
        "target_market": "DTC ecommerce brands with 5-50 employees.",
        "pricing_model": "subscription",
        "vertical": "enterprise",
        "summary_metrics": {
            "adoption_rate": 49.0,
            "churn_rate": 15.0,
            "viral_coefficient": 0.73,
            "confidence_score": 79.0,
            "total_adopters": 1860,
        },
        "key_insights": [
            {"insight": "Savings calculators unlock procurement buy-in during onboarding."},
            {"insight": "API integrations with fulfillment partners reduce churn risk."},
            {"insight": "Quarterly compliance reporting creates strong expansion paths."},
        ],
    },
    {
        "business_name": "Pop-up Fitness Quest",
        "idea_description": "Mobile app that turns city exploration into gamified group workout challenges.",
        "target_market": "Gen Z and young professionals in major metros.",
        "pricing_model": "freemium",
        "vertical": "consumer_app",
        "summary_metrics": {
            "adoption_rate": 64.0,
            "churn_rate": 31.0,
            "viral_coefficient": 1.55,
            "confidence_score": 66.0,
            "total_adopters": 3550,
        },
        "key_insights": [
            {"insight": "Team-based quests strongly outperform solo challenges on retention."},
            {"insight": "New-city launch kits shorten cold-start time by nearly two weeks."},
            {"insight": "Viral growth is tied to social sharing at challenge completion."},
        ],
    },
    {
        "business_name": "Micro Learning Sprints",
        "idea_description": "Short daily AI-generated lessons with adaptive quizzes for upskilling teams.",
        "target_market": "SMBs with distributed customer support and sales teams.",
        "pricing_model": "subscription",
        "vertical": "saas",
        "summary_metrics": {
            "adoption_rate": 69.0,
            "churn_rate": 17.0,
            "viral_coefficient": 0.98,
            "confidence_score": 83.0,
            "total_adopters": 4270,
        },
        "key_insights": [
            {"insight": "Managers drive adoption when progress is visible in team dashboards."},
            {"insight": "Learning streak mechanics significantly improve week-4 retention."},
            {"insight": "Course personalization quality is a key predictor of expansion."},
        ],
    },
    {
        "business_name": "Secondlife Furniture",
        "idea_description": "Marketplace for refurbished designer furniture with AR room previews.",
        "target_market": "Urban renters and design-conscious homeowners.",
        "pricing_model": "commission",
        "vertical": "marketplace",
        "summary_metrics": {
            "adoption_rate": 57.0,
            "churn_rate": 24.0,
            "viral_coefficient": 1.11,
            "confidence_score": 74.0,
            "total_adopters": 2790,
        },
        "key_insights": [
            {"insight": "Trust badges and restoration provenance increase conversion confidence."},
            {"insight": "AR placement reduces return rates in higher-value categories."},
            {"insight": "Supply liquidity is strongest when seller onboarding is concierge-led."},
        ],
    },
    {
        "business_name": "Indie Dev QA Cloud",
        "idea_description": "On-demand AI-assisted game QA with repro steps and severity triage.",
        "target_market": "Indie and AA game studios with small QA teams.",
        "pricing_model": "usage_based",
        "vertical": "enterprise",
        "summary_metrics": {
            "adoption_rate": 52.0,
            "churn_rate": 16.0,
            "viral_coefficient": 0.89,
            "confidence_score": 80.0,
            "total_adopters": 1640,
        },
        "key_insights": [
            {"insight": "Crash clustering and repro accuracy are top renewal drivers."},
            {"insight": "Studios prefer predictable pricing tiers over pure usage billing."},
            {"insight": "Integrations with issue trackers reduce friction at adoption."},
        ],
    },
    {
        "business_name": "Pet Health Companion",
        "idea_description": "AI pet-care planner with symptom journaling and vet handoff summaries.",
        "target_market": "Pet owners in North America and Europe.",
        "pricing_model": "freemium",
        "vertical": "consumer_app",
        "summary_metrics": {
            "adoption_rate": 63.0,
            "churn_rate": 26.0,
            "viral_coefficient": 1.21,
            "confidence_score": 71.0,
            "total_adopters": 3390,
        },
        "key_insights": [
            {"insight": "Medication reminders and vet visit prep are sticky core workflows."},
            {"insight": "Trust signals around medical disclaimers reduce support burden."},
            {"insight": "Community sharing boosts acquisition in breed-focused cohorts."},
        ],
    },
    {
        "business_name": "B2B Prompt Governance",
        "idea_description": "Policy and quality guardrails for enterprise AI prompts with audit trails.",
        "target_market": "Regulated enterprises adopting internal AI copilots.",
        "pricing_model": "subscription",
        "vertical": "enterprise",
        "summary_metrics": {
            "adoption_rate": 46.0,
            "churn_rate": 12.0,
            "viral_coefficient": 0.66,
            "confidence_score": 88.0,
            "total_adopters": 1180,
        },
        "key_insights": [
            {"insight": "Security and legal buyers require immutable audit logs from day one."},
            {"insight": "Model drift alerts improve trust for compliance-driven teams."},
            {"insight": "Deployment speed is the key tie-breaker vs internal tooling."},
        ],
    },
]


async def _ensure_seed_user(db) -> User:
    result = await db.execute(select(User).where(User.id == "trend_seed_user"))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(
        id="trend_seed_user",
        email="trending@futurus.dev",
        full_name="Trend Scout",
        plan_tier="open",
        credit_balance=0,
        subscription_status="inactive",
        created_at=_utcnow(),
        last_active_at=_utcnow(),
        onboarding_completed=True,
    )
    db.add(user)
    await db.flush()
    return user


def _build_report_payload(spec: dict[str, Any]) -> dict[str, Any]:
    summary = spec["summary_metrics"]
    return {
        "summary_metrics": summary,
        "adoption_curve": [
            {"turn": 1, "adopters": int(summary.get("total_adopters", 1000) * 0.15)},
            {"turn": 2, "adopters": int(summary.get("total_adopters", 1000) * 0.33)},
            {"turn": 3, "adopters": int(summary.get("total_adopters", 1000) * 0.61)},
            {"turn": 4, "adopters": int(summary.get("total_adopters", 1000) * 0.82)},
            {"turn": 5, "adopters": int(summary.get("total_adopters", 1000))},
        ],
        "persona_breakdown": [
            {"persona": "early_adopters", "share": 42},
            {"persona": "mainstream", "share": 37},
            {"persona": "skeptics", "share": 21},
        ],
        "failure_timeline": [],
        "risk_matrix": [
            {"risk": "acquisition_cost", "impact": "medium", "likelihood": "medium"},
            {"risk": "retention_drop", "impact": "high", "likelihood": "medium"},
        ],
        "pivot_suggestions": [
            {"title": "Niche-first go-to-market", "rationale": "Improves activation and lowers CAC."}
        ],
        "key_insights": spec["key_insights"],
        "viability_summary": {
            "headline": "Promising with execution risk",
            "confidence": int(summary.get("confidence_score", 70)),
            "verdict": "The idea shows healthy upside if retention and channel fit are actively managed.",
        },
        "ensemble_variance": {"spread": "medium"},
        "citations": [],
    }


async def _seed_trend_ideas(db, user: User) -> tuple[int, int]:
    created = 0
    updated = 0

    for spec in TREND_IDEAS:
        title = spec["business_name"]
        existing_idea_result = await db.execute(
            select(PublishedIdea).where(
                PublishedIdea.user_id == user.id,
                PublishedIdea.title == title,
            )
        )
        existing_idea = existing_idea_result.scalar_one_or_none()
        if existing_idea:
            continue

        simulation = Simulation(
            user_id=user.id,
            team_id=None,
            business_name=spec["business_name"],
            idea_description=spec["idea_description"],
            target_market=spec["target_market"],
            pricing_model=spec["pricing_model"],
            price_points={"base": 19},
            gtm_channels=["tiktok", "instagram", "seo"],
            competitors=["legacy incumbents", "niche startups"],
            key_assumptions=["clear ICP", "repeatable channel", "retention loop"],
            vertical=spec["vertical"],
            personas=[],
            agent_count=500,
            max_turns=20,
            ensemble_runs=3,
            plan_tier="open",
            status=SimulationStatus.COMPLETED,
            current_turn=20,
            agents_active=0,
            estimated_cost_usd=1.20,
            actual_cost_usd=1.07,
            created_at=_utcnow(),
            started_at=_utcnow(),
            completed_at=_utcnow(),
        )
        db.add(simulation)
        await db.flush()

        report_payload = _build_report_payload(spec)
        report = Report(
            simulation_id=simulation.id,
            **report_payload,
        )
        db.add(report)

        scores = compute_idea_scores(report.summary_metrics)
        published = PublishedIdea(
            simulation_id=simulation.id,
            user_id=user.id,
            user_name=user.full_name or "Trend Scout",
            user_avatar_url=user.avatar_url,
            title=simulation.business_name,
            description=simulation.idea_description,
            category=vertical_to_category(simulation.vertical),
            score_market_demand=scores["market_demand"],
            score_retention=scores["retention"],
            score_virality=scores["virality"],
            score_feasibility=scores["feasibility"],
            overall_rating=scores["overall"],
            score_breakdown=scores["breakdown"],
            is_active=True,
            created_at=_utcnow(),
        )
        db.add(published)
        created += 1

    # Backfill all existing ideas to ensure corrected score logic is applied.
    all_ideas_result = await db.execute(select(PublishedIdea))
    all_ideas = list(all_ideas_result.scalars())

    for idea in all_ideas:
        report_result = await db.execute(
            select(Report).where(Report.simulation_id == idea.simulation_id)
        )
        report = report_result.scalar_one_or_none()
        if not report or not isinstance(report.summary_metrics, dict):
            continue

        scores = compute_idea_scores(report.summary_metrics)
        old_tuple = (
            round(idea.score_market_demand, 1),
            round(idea.score_retention, 1),
            round(idea.score_virality, 1),
            round(idea.score_feasibility, 1),
            round(idea.overall_rating, 1),
        )
        new_tuple = (
            round(scores["market_demand"], 1),
            round(scores["retention"], 1),
            round(scores["virality"], 1),
            round(scores["feasibility"], 1),
            round(scores["overall"], 1),
        )

        if old_tuple != new_tuple:
            idea.score_market_demand = scores["market_demand"]
            idea.score_retention = scores["retention"]
            idea.score_virality = scores["virality"]
            idea.score_feasibility = scores["feasibility"]
            idea.overall_rating = scores["overall"]
            idea.score_breakdown = scores["breakdown"]
            updated += 1

    return created, updated


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        user = await _ensure_seed_user(db)
        created, updated = await _seed_trend_ideas(db, user)
        await db.commit()

    print(f"Seed complete: created={created}, rescored={updated}")


if __name__ == "__main__":
    asyncio.run(main())

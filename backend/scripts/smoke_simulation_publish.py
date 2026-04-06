import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.published_idea import PublishedIdea
from models.simulation import Report, Simulation, SimulationStatus
from models.user import User
from services.idea_rating import compute_idea_scores, vertical_to_category
from workers.simulation_worker import run_simulation_inline


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_smoke_user() -> User:
    async with AsyncSessionLocal() as db:
        user_id = "smoke-test-user"
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return user

        user = User(
            id=user_id,
            email="smoke-test@local.futurus",
            full_name="Smoke Test",
            plan_tier="pro",
            credit_balance=999,
            last_active_at=_now_utc(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def create_simulation(user: User) -> Simulation:
    async with AsyncSessionLocal() as db:
        sim = Simulation(
            id=uuid.uuid4(),
            user_id=user.id,
            business_name="Smoke Test: AI Retail Assistant",
            idea_description=(
                "AI shopping copilot for independent e-commerce stores that recommends products "
                "and optimizes bundles for higher conversion."
            ),
            target_market="Small D2C brands in US and EU",
            pricing_model="subscription",
            price_points={"starter": 49, "growth": 149},
            gtm_channels=["content", "partner_agencies", "product_hunt"],
            competitors=[{"name": "Nosto"}, {"name": "Rebuy"}],
            key_assumptions=[
                {"variable": "integration_time", "value": "< 1 day"},
                {"variable": "upsell_lift", "value": ">= 8%"},
            ],
            vertical="saas",
            personas=[],
            agent_count=10,
            max_turns=10,
            ensemble_runs=1,
            plan_tier="pro",
            status=SimulationStatus.QUEUED,
            started_at=_now_utc(),
        )
        db.add(sim)
        await db.commit()
        await db.refresh(sim)
        return sim


async def fetch_sim_and_report(sim_id: uuid.UUID) -> tuple[Simulation | None, Report | None]:
    async with AsyncSessionLocal() as db:
        sim_res = await db.execute(select(Simulation).where(Simulation.id == sim_id))
        sim = sim_res.scalar_one_or_none()
        report_res = await db.execute(select(Report).where(Report.simulation_id == sim_id))
        report = report_res.scalar_one_or_none()
        return sim, report


async def publish_if_possible(sim: Simulation, report: Report) -> PublishedIdea | None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(PublishedIdea).where(PublishedIdea.simulation_id == sim.id)
        )
        idea = existing.scalar_one_or_none()
        if idea:
            return idea

        scores = compute_idea_scores(report.summary_metrics or {})
        idea = PublishedIdea(
            simulation_id=sim.id,
            user_id=sim.user_id,
            user_name="Smoke Test",
            user_avatar_url=None,
            title=sim.business_name,
            description=sim.idea_description,
            category=vertical_to_category(sim.vertical),
            score_market_demand=scores["market_demand"],
            score_retention=scores["retention"],
            score_virality=scores["virality"],
            score_feasibility=scores["feasibility"],
            overall_rating=scores["overall"],
            score_breakdown=scores["breakdown"],
        )
        db.add(idea)
        await db.commit()
        await db.refresh(idea)
        return idea


def extract_validation_method(report: Report | None) -> str:
    if not report or not isinstance(report.viability_summary, dict):
        return "missing_viability_summary"
    stat = report.viability_summary.get("statistical_validation")
    if not isinstance(stat, dict):
        return "missing_statistical_validation"
    return str(stat.get("method") or "method_not_set")


async def main() -> int:
    user = await ensure_smoke_user()
    sim = await create_simulation(user)

    # Run inline worker synchronously so this script can verify completion.
    await asyncio.to_thread(run_simulation_inline, str(sim.id))

    final_sim, report = await fetch_sim_and_report(sim.id)
    if not final_sim:
        print("SMOKE_FAIL: simulation row missing after run")
        return 1
    if final_sim.status != SimulationStatus.COMPLETED:
        print(f"SMOKE_FAIL: simulation status={final_sim.status}")
        return 2
    if not report:
        print("SMOKE_FAIL: report missing")
        return 3

    idea = await publish_if_possible(final_sim, report)
    method = extract_validation_method(report)

    print("SMOKE_OK")
    print(f"simulation_id={final_sim.id}")
    print(f"report_id={report.id}")
    print(f"timesfm_method={method}")
    if idea:
        print(f"published_idea_id={idea.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

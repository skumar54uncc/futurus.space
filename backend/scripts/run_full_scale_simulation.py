import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.simulation import Report, Simulation, SimulationStatus
from models.user import User
from workers.simulation_worker import run_simulation_inline


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_runner_user() -> User:
    async with AsyncSessionLocal() as db:
        user_id = "full-scale-runner"
        row = await db.execute(select(User).where(User.id == user_id))
        user = row.scalar_one_or_none()
        if user:
            return user
        user = User(
            id=user_id,
            email="full-scale-runner@local.futurus",
            full_name="Full Scale Runner",
            plan_tier="enterprise",
            credit_balance=999,
            last_active_at=_utc_now(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def create_full_scale_sim(user: User) -> Simulation:
    async with AsyncSessionLocal() as db:
        sim = Simulation(
            id=uuid.uuid4(),
            user_id=user.id,
            business_name="Full-Scale Run: Omni Retail Assist",
            idea_description=(
                "AI co-pilot for retail operators to optimize merchandising, promotions, "
                "and customer support across online and in-store channels."
            ),
            target_market="SMB and mid-market omnichannel retailers in US and EU",
            pricing_model="subscription",
            price_points={"starter": 99, "pro": 299, "enterprise": 999},
            gtm_channels=["partner_agencies", "content", "sales_assisted"],
            competitors=[{"name": "Nosto"}, {"name": "Klaviyo"}, {"name": "Dynamic Yield"}],
            key_assumptions=[
                {"variable": "integration_time", "value": "< 2 weeks"},
                {"variable": "uplift_conversion", "value": ">= 7%"},
            ],
            vertical="saas",
            personas=[],
            agent_count=1000,
            max_turns=40,
            ensemble_runs=1,
            plan_tier="enterprise",
            status=SimulationStatus.QUEUED,
            started_at=_utc_now(),
        )
        db.add(sim)
        await db.commit()
        await db.refresh(sim)
        return sim


async def fetch_result(sim_id: uuid.UUID) -> tuple[Simulation | None, Report | None]:
    async with AsyncSessionLocal() as db:
        sim_row = await db.execute(select(Simulation).where(Simulation.id == sim_id))
        sim = sim_row.scalar_one_or_none()
        rep_row = await db.execute(select(Report).where(Report.simulation_id == sim_id))
        report = rep_row.scalar_one_or_none()
        return sim, report


async def main() -> int:
    user = await ensure_runner_user()
    sim = await create_full_scale_sim(user)

    await asyncio.to_thread(run_simulation_inline, str(sim.id))

    final_sim, report = await fetch_result(sim.id)
    if not final_sim:
        print("RUN_FAIL: simulation row missing")
        return 1

    print(f"simulation_id={sim.id}")
    print(f"status={final_sim.status}")
    print(f"actual_cost_usd={float(final_sim.actual_cost_usd or 0.0):.4f}")

    if report is None:
        print("RUN_FAIL: report missing")
        return 2

    viability = report.viability_summary or {}
    diag = viability.get("run_diagnostics", {}) if isinstance(viability, dict) else {}
    cache = viability.get("forecast_cache", {}) if isinstance(viability, dict) else {}

    print(f"report_id={report.id}")
    print(f"turn_diagnostics={diag}")
    print(f"forecast_cache={cache}")
    print(f"summary_metrics={report.summary_metrics}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

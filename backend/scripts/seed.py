"""Seeds DB with plans and a demo user."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.database import AsyncSessionLocal, engine, Base
from models.user import User
from datetime import datetime


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.id == "demo_user"))
        existing = result.scalar_one_or_none()
        if not existing:
            demo_user = User(
                id="demo_user",
                email="demo@futurus.dev",
                full_name="Demo Founder",
                plan_tier="open",
                credit_balance=0,
                subscription_status="inactive",
                created_at=datetime.utcnow(),
                last_active_at=datetime.utcnow(),
                onboarding_completed=True,
            )
            db.add(demo_user)
            await db.commit()
            print("Demo user created: demo@futurus.dev")
        else:
            print("Demo user already exists")


if __name__ == "__main__":
    asyncio.run(seed())

"""JWT verification middleware using Clerk."""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.security import verify_clerk_token
from models.user import User
from datetime import datetime
import structlog

logger = structlog.get_logger()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = await verify_clerk_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        email = payload.get("email", payload.get("email_addresses", [{}])[0].get("email_address", ""))
        user = User(
            id=user_id,
            email=email or f"{user_id}@clerk.user",
            full_name=payload.get("name", payload.get("first_name", "")),
            plan_tier="open",
            credit_balance=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("user_auto_created", user_id=user_id, email=user.email)

    user.last_active_at = datetime.utcnow()
    await db.commit()
    return user

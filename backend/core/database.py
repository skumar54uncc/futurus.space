from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from core.config import settings


def _asyncpg_connect_args(database_url: str) -> dict:
    """
    Supabase transaction pooler (PgBouncer) does not support asyncpg's default prepared
    statement cache → DuplicatePreparedStatementError. Disable cache for pooler URLs.
    """
    u = database_url.lower()
    if (
        "pooler.supabase" in u
        or ".pooler." in u
        or ":6543/" in u
        or ":6543?" in u
    ):
        return {"statement_cache_size": 0}
    return {}


engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    connect_args=_asyncpg_connect_args(settings.database_url),
    pool_pre_ping=True,          # Detect stale connections
    pool_size=5,                 # Conservative for Supabase free tier (25 max)
    max_overflow=10,
    pool_recycle=300,            # Recycle connections every 5 min
    pool_timeout=30,             # Wait max 30s for a connection
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

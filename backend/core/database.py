from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
from core.config import settings


def _pgbouncer_style_url(database_url: str) -> bool:
    """Supabase pooler (any mode) / port 6543 — PgBouncer breaks prepared statements + SQLAlchemy pooling."""
    u = database_url.lower()
    return "supabase" in u or "pooler" in u or ":6543" in u


# Always disable asyncpg's statement cache when using PgBouncer (transaction pooler, etc.).
# URL heuristics alone miss some Supabase formats; duplicate detection is brittle, so we always set 0.
_ASYNCPG_CONNECT_ARGS = {"statement_cache_size": 0}

if _pgbouncer_style_url(settings.database_url):
    # Open a fresh DBAPI connection per checkout — avoids stale server-side prepared stmt names via PgBouncer.
    engine = create_async_engine(
        settings.database_url,
        echo=settings.environment == "development",
        connect_args=_ASYNCPG_CONNECT_ARGS,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.environment == "development",
        connect_args=_ASYNCPG_CONNECT_ARGS,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        pool_timeout=30,
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

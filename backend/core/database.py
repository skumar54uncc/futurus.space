from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from core.config import settings


def _pgbouncer_style_url(database_url: str) -> bool:
    """Supabase pooler (any mode) / port 6543 — PgBouncer breaks prepared statements + SQLAlchemy pooling."""
    u = database_url.lower()
    return "supabase" in u or "pooler" in u or ":6543" in u


# PgBouncer (e.g. Supabase pooler / :6543): asyncpg + SQLAlchemy both cache/use named PREPAREs.
# - statement_cache_size: asyncpg client cache (see asyncpg DuplicatePreparedStatementError hint).
# - prepared_statement_cache_size: SQLAlchemy asyncpg dialect LRU (defaults to 100 if omitted).
# - prepared_statement_name_func: avoid reused names like __asyncpg_stmt_1__ on pooled backends.
_ASYNCPG_CONNECT_ARGS = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__",
}

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
    # Default pool for create_async_engine is async-compatible (do not use sync QueuePool).
    engine = create_async_engine(
        settings.database_url,
        echo=settings.environment == "development",
        connect_args=_ASYNCPG_CONNECT_ARGS,
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

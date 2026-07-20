"""Lease-based simulation recovery helpers (startup reaping)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from models.simulation import SimulationStatus

# Active work must keep last_heartbeat_at fresh. Longer than a typical LLM stall,
# shorter than "spin forever" after an instance death.
LEASE_SECONDS = 25 * 60
QUEUED_MAX_AGE = timedelta(hours=6)

ACTIVE_STATUSES = (
    SimulationStatus.BUILDING_SEED,
    SimulationStatus.GENERATING_PERSONAS,
    SimulationStatus.RUNNING,
    SimulationStatus.GENERATING_REPORT,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def effective_heartbeat(
    last_heartbeat_at: datetime | None,
    started_at: datetime | None,
    created_at: datetime | None,
) -> datetime | None:
    """Prefer explicit heartbeat; fall back so pre-migration rows still reap safely."""
    return last_heartbeat_at or started_at or created_at


def should_reap_active(
    *,
    now: datetime,
    last_heartbeat_at: datetime | None,
    started_at: datetime | None,
    created_at: datetime | None,
    lease_seconds: int = LEASE_SECONDS,
) -> bool:
    """True when an in-flight sim's lease has expired (worker likely dead)."""
    hb = effective_heartbeat(last_heartbeat_at, started_at, created_at)
    if hb is None:
        return True
    if hb.tzinfo is None:
        hb = hb.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - hb).total_seconds() > lease_seconds


def should_reap_queued(
    *,
    now: datetime,
    created_at: datetime | None,
    max_age: timedelta = QUEUED_MAX_AGE,
) -> bool:
    if created_at is None:
        return True
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return created_at < (now - max_age)

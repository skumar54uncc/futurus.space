"""TDD: lease-based recovery must not reap heartbeating sims; must reap dead leases."""

from datetime import datetime, timedelta, timezone

from services.simulation_recovery import (
    LEASE_SECONDS,
    should_reap_active,
    should_reap_queued,
)


def _t(minutes_ago: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)


def test_fresh_heartbeat_not_reaped():
    now = _t(0)
    assert not should_reap_active(
        now=now,
        last_heartbeat_at=_t(5),
        started_at=_t(60),
        created_at=_t(60),
    )


def test_stale_heartbeat_reaped_even_if_created_recently():
    """Age-only reaping was wrong the other way too; lease is the signal."""
    now = _t(0)
    assert should_reap_active(
        now=now,
        last_heartbeat_at=_t((LEASE_SECONDS / 60) + 5),
        started_at=_t(10),
        created_at=_t(10),
        lease_seconds=LEASE_SECONDS,
    )


def test_null_heartbeat_uses_started_at_fallback():
    now = _t(0)
    # Recent start, no heartbeat column yet → keep
    assert not should_reap_active(
        now=now,
        last_heartbeat_at=None,
        started_at=_t(10),
        created_at=_t(10),
    )
    # Old start, no heartbeat → reap
    assert should_reap_active(
        now=now,
        last_heartbeat_at=None,
        started_at=_t(40),
        created_at=_t(40),
    )


def test_healthy_long_running_sim_kept_via_heartbeat():
    """Sim created hours ago but still heartbeating must survive startup."""
    now = _t(0)
    assert not should_reap_active(
        now=now,
        last_heartbeat_at=_t(2),
        started_at=_t(180),
        created_at=_t(180),
    )


def test_queued_only_reaped_when_old():
    now = _t(0)
    assert not should_reap_queued(now=now, created_at=_t(60))  # 1h
    assert should_reap_queued(now=now, created_at=_t(60 * 7))  # 7h

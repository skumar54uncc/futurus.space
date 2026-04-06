"""Periodic Celery tasks for Futurus automation."""

from __future__ import annotations

import asyncio

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="refresh_daily_macro_context")
def refresh_daily_macro_context_task() -> dict:
    from services.mirai_lite import refresh_daily_macro_context

    payload = asyncio.run(refresh_daily_macro_context())
    logger.info("daily_macro_context_refreshed", shocks=len(payload.get("shocks", [])))
    return payload

from celery import Celery
from celery.schedules import crontab
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "futurus",
    broker=redis_url,
    backend=redis_url,
    include=["workers.simulation_worker", "workers.report_worker", "workers.periodic_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,
    task_soft_time_limit=1500,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    beat_schedule={
        "refresh-daily-mirai-lite-context": {
            "task": "refresh_daily_macro_context",
            "schedule": crontab(minute=0, hour=3),
        },
    },
)

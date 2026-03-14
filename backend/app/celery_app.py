"""
Celery app for async tasks (enrichers, scans).
Broker and result backend: Redis.
"""

from celery import Celery
import os

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "netscout",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.investigation_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

"""Celery application. Start a worker with:

celery -A app.workers.celery_app worker --loglevel=INFO --concurrency=1
(add --pool=solo on Windows)
"""

from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level, settings.log_json)

celery_app = Celery("techprep", broker=settings.redis_url, include=["app.workers.tasks"])
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,  # status lives in Postgres, not in a result backend
    task_acks_late=True,  # a task is only removed from the queue after it finished
    task_reject_on_worker_lost=True,  # ...so a crashed worker's task is redelivered
    worker_prefetch_multiplier=1,  # long CPU tasks: don't hoard messages
    broker_connection_retry_on_startup=True,
    task_time_limit=15 * 60,
    task_soft_time_limit=14 * 60,
)

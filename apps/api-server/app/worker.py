from celery import Celery

from .config import settings

celery = Celery("legal_platform", broker=settings.redis_url, backend=settings.redis_url)


@celery.task
def health_task() -> str:
    return "ok"


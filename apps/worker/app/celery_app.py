from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "stellar_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.stellar_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Periodic tasks configuration
celery_app.conf.beat_schedule = {
    'operations-stream-every-minute': {
        'task': 'app.tasks.stellar_tasks.ingest_operations_stream',
        'schedule': 60.0,  # Every 60 seconds
    },
    'update-network-stats-every-5-minutes': {
        'task': 'app.tasks.stellar_tasks.update_network_stats',
        'schedule': 300.0,  # Every 5 minutes
    },
    'run-rule-engine': {
        'task': 'app.tasks.stellar_tasks.run_rule_engine',
        'schedule': settings.RULE_ENGINE_INTERVAL_MINUTES * 60.0,  # Configurable interval
    },
}

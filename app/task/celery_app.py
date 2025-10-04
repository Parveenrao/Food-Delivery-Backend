from celery import Celery
from app.config import settings

celery_app = Celery(
    "food_deliver",
    broker  = settings.CELERY_BROKER_URL,
    backend = settings.CELERY_RESULT_BACKEND,
    
    include=[
        "app.task.order_task",
        "app.task.notification_task",
        "app.task.payment_task"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=60,  # 1 minute
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,)



celery_app.conf.beat_schedule = {
    "check-payment-status": {
        "task": "app.tasks.payment_tasks.check_pending_payments",
        "schedule": 60.0,  # Run every minute
    },
    "update-order-status": {
        "task": "app.tasks.order_tasks.update_estimated_delivery_times",
        "schedule": 300.0,  # Run every 5 minutes
    },
}
    
    
    
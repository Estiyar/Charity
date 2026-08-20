import os

from celery import Celery
from kombu import Queue

from ekomek_common.constants import SERVICE_QUEUES


def create_celery_app(service_name):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    app = Celery(service_name)
    app.config_from_object("django.conf:settings", namespace="CELERY")
    event_queue = SERVICE_QUEUES[service_name]
    app.conf.task_queues = (
        Queue(f"{service_name}.tasks"),
        Queue(event_queue),
    )
    app.conf.task_default_queue = f"{service_name}.tasks"
    app.autodiscover_tasks()
    return app

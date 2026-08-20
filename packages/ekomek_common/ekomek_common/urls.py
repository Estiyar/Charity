from django.urls import path

from ekomek_common.health import HealthView
from ekomek_common.metrics import MetricsView


def infrastructure_urlpatterns():
    return [
        path("health/", HealthView.as_view(), name="health"),
        path("metrics/", MetricsView.as_view(), name="metrics"),
    ]

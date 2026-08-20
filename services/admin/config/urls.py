from django.urls import include, path

from ekomek_common.urls import infrastructure_urlpatterns

urlpatterns = infrastructure_urlpatterns() + [
    path("", include("admin_service.urls")),
]

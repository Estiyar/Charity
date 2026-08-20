from django.http import HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

REQUEST_COUNT = Counter(
    "ekomek_http_requests_total",
    "HTTP requests",
    ["service", "method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "ekomek_http_request_latency_seconds",
    "HTTP request latency",
    ["service", "method"],
)


class MetricsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)

from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        from django.conf import settings

        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False
        status_code = 200 if db_ok else 503
        return Response(
            {
                "status": "ok" if db_ok else "degraded",
                "service": settings.SERVICE_NAME,
                "database": "up" if db_ok else "down",
            },
            status=status_code,
        )

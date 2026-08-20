from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import Notification
from .repositories import NotificationRepository
from .serializers import NotificationSerializer
from .services import mark_notification_read, mark_notification_unread


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get(self, request):
        unread_param = request.query_params.get("unread")
        unread = None
        if unread_param in {"1", "true", "True"}:
            unread = True
        elif unread_param in {"0", "false", "False"}:
            unread = False
        notification_type = request.query_params.get("type", "")
        repository = NotificationRepository()
        queryset = repository.for_recipient(
            request.user.id,
            unread=unread,
            notification_type=notification_type,
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        items = page if page is not None else queryset
        data = NotificationSerializer(items, many=True).data
        if page is None:
            return Response(
                {
                    "count": len(data),
                    "unread_count": repository.unread_count(request.user.id),
                    "results": data,
                }
            )
        response = paginator.get_paginated_response(data)
        response.data["unread_count"] = repository.unread_count(request.user.id)
        return response


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        item = Notification.objects.filter(pk=pk, recipient_id=request.user.id).first()
        if item is None:
            return Response({"detail": "Not found."}, status=404)
        return Response(NotificationSerializer(mark_notification_read(item)).data)


class NotificationUnreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        item = Notification.objects.filter(pk=pk, recipient_id=request.user.id).first()
        if item is None:
            return Response({"detail": "Not found."}, status=404)
        return Response(NotificationSerializer(mark_notification_unread(item)).data)


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = NotificationRepository().mark_all_read(request.user.id)
        return Response({"updated": updated, "read_at": timezone.now().isoformat()})

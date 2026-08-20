from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken

from .models import User
from .repositories import UserRepository
from .serializers import InternalUserSerializer, InternalUserSetStatusSerializer
from .services import set_user_status


class InternalUserListView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request):
        users = UserRepository().list_filtered(
            status=request.query_params.get("status"),
            role=request.query_params.get("role"),
        )
        return Response(InternalUserSerializer(users, many=True).data)


class InternalUserSetStatusView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if user is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = InternalUserSetStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = set_user_status(
            user,
            serializer.validated_data["status"],
            serializer.validated_data.get("reason", ""),
        )
        return Response(InternalUserSerializer(user).data)

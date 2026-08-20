from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import IsAdmin
from ekomek_common.constants import Role
from ekomek_common.http import ServiceClientError
from ekomek_common.outbox import enqueue_event

from .models import Profile
from .serializers import AdminProfileUpdateSerializer, OwnerProfileSerializer, PublicProfileSerializer, StaffProfileSerializer
from .services import apply_admin_updates, load_profile


def profile_defaults_from_user(user):
    return {
        "full_name": getattr(user, "full_name", "") or "",
        "email": getattr(user, "email", "") or "",
        "role": getattr(user, "role", "") or "",
        "verification_status": getattr(user, "status", "") or "",
    }


def serialize_profile(profile, request):
    user = request.user
    if getattr(user, "is_authenticated", False) and user.id == profile.user_id:
        return OwnerProfileSerializer(profile, context={"request": request})
    if getattr(user, "is_authenticated", False) and getattr(user, "role", None) in Role.STAFF:
        return StaffProfileSerializer(profile, context={"request": request})
    return PublicProfileSerializer(profile, context={"request": request})


class MeProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        profile = load_profile(request.user.id, request.user, profile_defaults_from_user(request.user))
        return Response(OwnerProfileSerializer(profile, context={"request": request}).data)

    def patch(self, request):
        profile = load_profile(request.user.id, request.user, profile_defaults_from_user(request.user))
        serializer = OwnerProfileSerializer(
            profile, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        enqueue_event(
            "profile.updated",
            "profile",
            profile.user_id,
            {"user_id": profile.user_id, "fields": sorted(serializer.validated_data.keys())},
        )
        return Response(OwnerProfileSerializer(profile, context={"request": request}).data)


class ProfileDetailView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [IsAdmin()]
        return [AllowAny()]

    def get(self, request, user_id):
        is_owner = getattr(request.user, "is_authenticated", False) and request.user.id == user_id
        is_staff = getattr(request.user, "is_authenticated", False) and getattr(request.user, "role", None) in Role.STAFF
        profile = Profile.objects.filter(user_id=user_id).first()
        if profile is None and (is_owner or is_staff):
            viewer = request.user if is_owner else None
            defaults = profile_defaults_from_user(request.user) if is_owner else None
            profile = load_profile(user_id, viewer, defaults)
        elif profile is not None:
            viewer = request.user if getattr(request.user, "is_authenticated", False) else None
            profile = load_profile(user_id, viewer)
        if profile is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_profile(profile, request).data)

    def patch(self, request, user_id):
        profile = Profile.objects.filter(user_id=user_id).first()
        if profile is None:
            profile = load_profile(user_id)
        serializer = AdminProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            apply_admin_updates(profile, dict(serializer.validated_data))
        except ServiceClientError:
            return Response(
                {"detail": "Не удалось сохранить поля ЭЦП в сервисе идентификации."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(StaffProfileSerializer(profile, context={"request": request}).data)

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsAuthor, IsModeratorOrAdmin
from ekomek_common.constants import Role
from ekomek_common.validators import validate_iin

from .beneficiary_serializers import (
    BeneficiarySerializer,
    BeneficiaryUpdateSerializer,
    InternalBeneficiarySerializer,
    InternalBeneficiaryUpsertSerializer,
    PublicBeneficiarySerializer,
    RepresentationSerializer,
)
from .beneficiary_services import (
    ensure_representation,
    update_beneficiary_visibility,
    upsert_beneficiary,
)
from .models import Beneficiary
from .repositories import BeneficiaryRepository, RepresentationRepository


def can_manage_beneficiary(user, beneficiary):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "role", None) in Role.STAFF:
        return True
    return beneficiary.owner_user_id == user.id


class BeneficiaryListView(APIView):
    permission_classes = [IsAuthenticated, IsAuthor]

    def get(self, request):
        items = BeneficiaryRepository().list_for_owner(request.user.id)
        return Response(BeneficiarySerializer(items, many=True).data)


class BeneficiaryDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        item = BeneficiaryRepository().get(pk)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if item.closed and not can_manage_beneficiary(request.user, item):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if can_manage_beneficiary(request.user, item):
            return Response(BeneficiarySerializer(item).data)
        return Response(PublicBeneficiarySerializer(item).data)

    def patch(self, request, pk):
        if not getattr(request.user, "is_authenticated", False):
            return Response({"detail": "Authentication credentials were not provided."}, status=401)
        if request.user.role != Role.AUTHOR and request.user.role not in Role.STAFF:
            return Response({"detail": "Нет доступа."}, status=403)
        item = BeneficiaryRepository().get_for_owner(request.user.id, pk) if request.user.role == Role.AUTHOR else BeneficiaryRepository().get(pk)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BeneficiaryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_beneficiary_visibility(item, **serializer.validated_data)
        return Response(BeneficiarySerializer(updated).data)


class InternalBeneficiaryUpsertView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request):
        serializer = InternalBeneficiaryUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            validate_iin(data["iin"])
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        beneficiary, _created = upsert_beneficiary(data["owner_user_id"], data["iin"], data["snapshot"])
        representation = ensure_representation(
            data["owner_user_id"],
            beneficiary,
            data["relationship_type"],
            data.get("verification_method") or "",
        )
        payload = InternalBeneficiarySerializer(beneficiary, context={"request": request}).data
        payload["iin"] = data["iin"]
        payload["representation"] = RepresentationSerializer(representation).data
        return Response(payload, status=status.HTTP_201_CREATED)


class InternalBeneficiaryDetailView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        item = Beneficiary.objects.filter(pk=pk).first()
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = InternalBeneficiarySerializer(item, context={"request": request}).data
        author_id = request.query_params.get("author_id")
        if author_id:
            representation = RepresentationRepository().get_for_author_beneficiary(int(author_id), pk)
            payload["representation"] = RepresentationSerializer(representation).data if representation else None
        return Response(payload)

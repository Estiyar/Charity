from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsAuthor, IsModeratorOrAdmin

from .beneficiary_serializers import (
    RepresentationRejectSerializer,
    RepresentationSerializer,
    RepresentationVerifySerializer,
)
from .beneficiary_services import (
    RepresentationActionError,
    confirm_representation,
    reject_representation,
    submit_representation_verification,
)
from .repositories import RepresentationRepository


class RepresentationListView(APIView):
    permission_classes = [IsAuthenticated, IsAuthor]

    def get(self, request):
        items = RepresentationRepository().list_for_author(request.user.id)
        return Response(RepresentationSerializer(items, many=True).data)


class RepresentationVerifyView(APIView):
    permission_classes = [IsAuthenticated, IsAuthor]

    def post(self, request):
        serializer = RepresentationVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        representation = RepresentationRepository().get(serializer.validated_data["representation_id"])
        if representation is None or representation.author_id != request.user.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        updated = submit_representation_verification(
            representation,
            serializer.validated_data["verification_method"],
            serializer.validated_data.get("document_ids"),
        )
        return Response(RepresentationSerializer(updated).data)


class StaffRepresentationListView(APIView):
    permission_classes = [IsAuthenticated, IsModeratorOrAdmin]

    def get(self, request):
        items = RepresentationRepository().list_for_moderation(request.query_params.get("status"))
        return Response(RepresentationSerializer(items, many=True).data)


class StaffRepresentationConfirmView(APIView):
    permission_classes = [IsAuthenticated, IsModeratorOrAdmin]

    def post(self, request, pk):
        item = RepresentationRepository().get(pk)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        updated = confirm_representation(item, verified_by=request.user.id)
        return Response(RepresentationSerializer(updated).data)


class StaffRepresentationRejectView(APIView):
    permission_classes = [IsAuthenticated, IsModeratorOrAdmin]

    def post(self, request, pk):
        item = RepresentationRepository().get(pk)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = RepresentationRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = reject_representation(
                item,
                serializer.validated_data["reason"],
                rejected_by=request.user.id,
            )
        except RepresentationActionError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RepresentationSerializer(updated).data)


class InternalRepresentationDetailView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        item = RepresentationRepository().get(pk)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(RepresentationSerializer(item).data)


class InternalRepresentationConfirmView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        item = RepresentationRepository().get(pk)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        updated = confirm_representation(item, verified_by=request.data.get("verified_by"))
        return Response(RepresentationSerializer(updated).data)

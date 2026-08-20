from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsAuthor, IsModerator
from ekomek_common.constants import PUBLIC_CARD_STATUSES
from .access_services import (
    can_manage_documents,
    duplicate_matches_for_card,
    fetch_card,
    mark_rejected,
    mark_revision_required,
    mark_verified,
)
from .expiry_services import expire_due_documents
from .models import Document
from .repositories import DocumentRepository
from .serializers import (
    DocumentModerationSerializer,
    DocumentVersionSerializer,
    DocumentWriteSerializer,
    PublicDocumentSerializer,
    StaffDocumentSerializer,
)
from .version_services import DuplicateDocumentFile, card_allows_upload, create_document_version


def _card_or_404(card_id):
    card = fetch_card(card_id)
    if card is None:
        raise Http404
    return card


class CardDocumentListCreateView(generics.ListCreateAPIView):
    pagination_class = None
    serializer_class = StaffDocumentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthor()]
        return [AllowAny()]

    def get_queryset(self):
        expire_due_documents(self.kwargs["pk"])
        return DocumentRepository().for_card(self.kwargs["pk"])

    def list(self, request, *args, **kwargs):
        card = _card_or_404(self.kwargs["pk"])
        if not can_manage_documents(request.user, card):
            return Response({"detail": "Нет доступа к документам."}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        card = _card_or_404(self.kwargs["pk"])
        if card["author_id"] != request.user.id:
            raise Http404
        if not card_allows_upload(card):
            return Response(
                {"detail": "Загружать документы можно только для редактируемой карточки."},
                status=400,
            )
        serializer = DocumentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            document = create_document_version(
                card["id"],
                serializer.validated_data.pop("file"),
                actor=request.user,
                attrs=serializer.validated_data,
            )
        except DuplicateDocumentFile as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return Response({"file": [message]}, status=400)
        except ValidationError as exc:
            detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
            return Response(detail, status=400)
        return Response(StaffDocumentSerializer(document).data, status=201)


class CardPublicDocumentListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    pagination_class = None
    serializer_class = PublicDocumentSerializer

    def get_queryset(self):
        expire_due_documents(self.kwargs["pk"])
        card = _card_or_404(self.kwargs["pk"])
        if card.get("status") not in PUBLIC_CARD_STATUSES:
            raise Http404
        return DocumentRepository().public_for_card(self.kwargs["pk"])


class DocumentVersionListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        document = Document.objects.filter(pk=pk).select_related("current_version").first()
        if document is None:
            return Response({"detail": "Not found."}, status=404)
        card = _card_or_404(document.card_id)
        if not can_manage_documents(request.user, card):
            return Response({"detail": "Нет доступа к документам."}, status=403)
        versions = document.versions.select_related("supersedes").all()
        return Response(DocumentVersionSerializer(versions, many=True).data)


class DocumentVerifyView(APIView):
    permission_classes = [IsModerator]

    def post(self, request, pk):
        document = Document.objects.filter(pk=pk).select_related("current_version").first()
        if document is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = DocumentModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("visibility"):
            document.visibility = data["visibility"]
            document.save(update_fields=["visibility", "updated_at"])
        mark_verified(
            document,
            actor=request.user,
            comment=data.get("comment") or "",
            has_confidential=data.get("has_confidential"),
        )
        document.refresh_from_db()
        return Response(StaffDocumentSerializer(document).data)


class DocumentRejectView(APIView):
    permission_classes = [IsModerator]

    def post(self, request, pk):
        document = Document.objects.filter(pk=pk).select_related("current_version").first()
        if document is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = DocumentModerationSerializer(data=request.data, context={"comment_required": True})
        serializer.is_valid(raise_exception=True)
        mark_rejected(document, actor=request.user, comment=serializer.validated_data["comment"])
        document.refresh_from_db()
        return Response(StaffDocumentSerializer(document).data)


class DocumentRequestRevisionView(APIView):
    permission_classes = [IsModerator]

    def post(self, request, pk):
        document = Document.objects.filter(pk=pk).select_related("current_version").first()
        if document is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = DocumentModerationSerializer(data=request.data, context={"comment_required": True})
        serializer.is_valid(raise_exception=True)
        try:
            mark_revision_required(
                document,
                actor=request.user,
                comment=serializer.validated_data["comment"],
                internal_comment=serializer.validated_data.get("internal_comment") or "",
            )
        except ValidationError as exc:
            detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
            return Response(detail if isinstance(detail, dict) else {"detail": str(exc)}, status=400)
        document.refresh_from_db()
        return Response(StaffDocumentSerializer(document, context={"request": request}).data)


class ModerationDocumentListView(generics.ListAPIView):
    permission_classes = [IsModerator]
    serializer_class = StaffDocumentSerializer
    pagination_class = None

    def get_queryset(self):
        expire_due_documents()
        return DocumentRepository().pending_review()


class InternalDocumentsView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        expire_due_documents(pk)
        documents = DocumentRepository().for_card(pk)
        return Response(StaffDocumentSerializer(documents, many=True).data)


class InternalStatsView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request):
        return Response({"verified_documents": DocumentRepository().verified_count()})


class InternalDocumentDuplicatesView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request):
        card_id = request.query_params.get("card_id")
        if not card_id:
            return Response({"detail": "card_id is required."}, status=400)
        return Response(duplicate_matches_for_card(int(card_id)))

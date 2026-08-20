from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ekomek_common.audit import log_sensitive_access

from .access_services import can_view_original, can_view_public_copy
from .audit_services import record_document_event
from .models import Document, DocumentVersion


def _document_or_404(pk):
    document = Document.objects.filter(pk=pk).select_related("current_version").first()
    if document is None:
        raise Http404
    return document


def _version_for(document, version_id):
    if not version_id:
        return document.current_version
    try:
        parsed = int(version_id)
    except (TypeError, ValueError):
        return None
    return DocumentVersion.objects.filter(pk=parsed, document=document).first()


class DocumentOriginalView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        document = _document_or_404(pk)
        if not can_view_original(request.user, document):
            raise Http404
        version = _version_for(document, request.query_params.get("version_id"))
        if version is None or not version.original_file:
            raise Http404
        log_sensitive_access(
            resource_type="document",
            resource_id=document.id,
            field_name="original_file",
            purpose="moderation_review",
            request=request,
        )
        record_document_event(document, "original_accessed", version=version, request=request)
        return FileResponse(version.original_file.open("rb"), filename=version.file_name)


class DocumentPublicFileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        document = _document_or_404(pk)
        if not can_view_public_copy(request.user, document):
            raise Http404
        version = document.current_version
        if version is None or not version.public_file:
            raise Http404
        return FileResponse(version.public_file.open("rb"), filename=version.public_file.name)

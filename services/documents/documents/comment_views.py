from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import IsModerator

from .comment_models import DocumentModeratorComment
from .comment_services import DocumentCommentSerializer, edit_document_comment


class DocumentCommentEditView(APIView):
    permission_classes = [IsModerator]

    def patch(self, request, pk, comment_id):
        comment = DocumentModeratorComment.objects.filter(pk=comment_id, document_id=pk).first()
        if comment is None:
            return Response({"detail": "Not found."}, status=404)
        try:
            comment = edit_document_comment(comment, request.data.get("body", ""), actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(DocumentCommentSerializer(comment).data)

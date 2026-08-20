from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import IsModeratorOrAdmin

from .comment_models import ModerationComment
from .comment_services import StoredModerationCommentSerializer, edit_moderation_comment, list_moderation_comments


class ModerationCommentListView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request):
        target_type = request.query_params.get("target_type")
        target_id = request.query_params.get("target_id")
        if not target_type or not target_id:
            return Response({"detail": "target_type и target_id обязательны."}, status=400)
        return Response(
            list_moderation_comments(
                target_type,
                int(target_id),
                user=request.user,
                include_internal=True,
            )
        )


class ModerationCommentEditView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def patch(self, request, pk):
        comment = ModerationComment.objects.filter(pk=pk).first()
        if comment is None:
            return Response({"detail": "Not found."}, status=404)
        try:
            comment = edit_moderation_comment(comment, request.data.get("body", ""), actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(StoredModerationCommentSerializer(comment).data)

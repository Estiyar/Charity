from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsModeratorOrAdmin
from ekomek_common.constants import Role

from .comment_models import CardModeratorComment
from .comment_services import CardCommentSerializer, edit_card_comment, serialize_card_comments
from .models import FundraisingCard


def _can_view_card_comments(user, card):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.role in Role.STAFF:
        return True
    return user.role == Role.AUTHOR and card.author_id == user.id


class CardCommentListView(APIView):
    def get_permissions(self):
        return []

    def get(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        if not _can_view_card_comments(request.user, card):
            return Response({"detail": "Not found."}, status=404)
        include_internal = getattr(request.user, "role", None) in Role.STAFF
        return Response(serialize_card_comments(card, user=request.user, include_internal=include_internal))


class CardCommentEditView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def patch(self, request, pk, comment_id):
        comment = CardModeratorComment.objects.filter(pk=comment_id, card_id=pk).first()
        if comment is None:
            return Response({"detail": "Not found."}, status=404)
        try:
            comment = edit_card_comment(comment, request.data.get("body", ""), actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(CardCommentSerializer(comment).data)


class InternalCardCommentListView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        return Response(serialize_card_comments(card, include_internal=True))

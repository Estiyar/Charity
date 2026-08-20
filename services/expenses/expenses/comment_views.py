from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import IsModerator

from .comment_models import ExpenseModeratorComment
from .comment_services import ExpenseCommentSerializer, edit_expense_comment


class ExpenseCommentEditView(APIView):
    permission_classes = [IsModerator]

    def patch(self, request, pk, comment_id):
        comment = ExpenseModeratorComment.objects.filter(pk=comment_id, expense_id=pk).first()
        if comment is None:
            return Response({"detail": "Not found."}, status=404)
        try:
            comment = edit_expense_comment(comment, request.data.get("body", ""), actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ExpenseCommentSerializer(comment).data)

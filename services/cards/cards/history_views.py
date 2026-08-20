from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.constants import Role

from .history_serializers import PublicHistorySerializer, StaffHistorySerializer
from .history_services import public_timeline, staff_history
from .models import FundraisingCard
from .trust_services import build_trust_status


def _can_see_card(user, card):
    if card.is_public:
        return True
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "role", None) in Role.STAFF:
        return True
    return getattr(user, "role", None) == Role.AUTHOR and card.author_id == user.id


class CardTrustStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        if not _can_see_card(request.user, card):
            raise Http404
        return Response(build_trust_status(card))


class CardHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        if not _can_see_card(request.user, card):
            raise Http404
        user = request.user
        if getattr(user, "is_authenticated", False) and getattr(user, "role", None) in Role.STAFF:
            return Response(StaffHistorySerializer(staff_history(card), many=True).data)
        return Response(PublicHistorySerializer(public_timeline(card), many=True).data)

from django.db.models import Q

from ekomek_common.constants import ACTIVE_FUNDRAISER_STATUSES, PUBLIC_CARD_STATUSES

from .models import FundraisingCard


class CardRepository:
    def get(self, pk):
        return FundraisingCard.objects.filter(pk=pk).first()

    def public_qs(self):
        return FundraisingCard.objects.filter(status__in=PUBLIC_CARD_STATUSES)

    def for_author(self, author_id):
        return FundraisingCard.objects.filter(author_id=author_id).order_by("-created_at")

    def visible_qs(self, user):
        queryset = FundraisingCard.objects.all()
        if not getattr(user, "is_authenticated", False):
            return queryset.filter(status__in=PUBLIC_CARD_STATUSES)
        if getattr(user, "role", None) in ("moderator", "admin"):
            return queryset
        if getattr(user, "role", None) == "author":
            from django.db.models import Q

            return queryset.filter(Q(status__in=PUBLIC_CARD_STATUSES) | Q(author_id=user.id))
        return queryset.filter(status__in=PUBLIC_CARD_STATUSES)

    def author_has_active(self, author_id):
        return FundraisingCard.objects.filter(
            author_id=author_id,
            status__in=ACTIVE_FUNDRAISER_STATUSES,
        ).exists()

    def recipient_has_active(self, iin_hash):
        if not iin_hash:
            return False
        return FundraisingCard.objects.filter(
            iin_hash=iin_hash,
            status__in=ACTIVE_FUNDRAISER_STATUSES,
        ).exists()

    def list_for_beneficiary(self, beneficiary_id):
        return FundraisingCard.objects.filter(beneficiary_id=beneficiary_id).order_by("-created_at")

    def list_admin(self):
        return FundraisingCard.objects.order_by("-created_at")

    def list_by_status(self, status_value=None, statuses=None):
        queryset = FundraisingCard.objects.all()
        if status_value:
            return queryset.filter(status=status_value).order_by("-updated_at")
        if statuses:
            return queryset.filter(status__in=statuses).order_by("-updated_at")
        return queryset.order_by("-updated_at")

    def duplicate_candidates(self, card):
        query = Q(pk__in=[])
        if card.iin_hash:
            query |= Q(iin_hash=card.iin_hash)
        if card.document_number_hash:
            query |= Q(document_number_hash=card.document_number_hash)
        if card.payout_details_hash:
            query |= Q(payout_details_hash=card.payout_details_hash)
        if card.request_fingerprint_hash:
            query |= Q(request_fingerprint_hash=card.request_fingerprint_hash)
        diagnosis = (card.diagnosis or "").strip()
        if diagnosis:
            query |= Q(diagnosis__iexact=diagnosis)
        query |= Q(author_id=card.author_id)
        return FundraisingCard.objects.exclude(pk=card.pk).filter(query)

    def other_author_cards(self, card):
        return FundraisingCard.objects.filter(author_id=card.author_id).exclude(pk=card.pk)

    def other_fingerprint_cards(self, card):
        if not card.request_fingerprint_hash:
            return FundraisingCard.objects.none()
        return FundraisingCard.objects.filter(
            request_fingerprint_hash=card.request_fingerprint_hash
        ).exclude(pk=card.pk)

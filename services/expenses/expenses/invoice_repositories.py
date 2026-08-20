from decimal import Decimal

from .payout_models import Invoice, InvoiceStatus, Payout, PayoutStatus

OPEN_INVOICE_STATUSES = {
    InvoiceStatus.PENDING_VERIFICATION,
    InvoiceStatus.VERIFIED,
    InvoiceStatus.PARTIALLY_PAID,
}
INFLIGHT_PAYOUT_STATUSES = {PayoutStatus.REQUESTED, PayoutStatus.PROCESSING}
PUBLIC_PAYOUT_STATUSES = {PayoutStatus.SUCCEEDED}


class InvoiceRepository:
    def for_card(self, card_id):
        return Invoice.objects.filter(card_id=card_id).select_related("organization").order_by("-created_at")

    def pending_review(self):
        return Invoice.objects.filter(status=InvoiceStatus.PENDING_VERIFICATION).select_related(
            "organization"
        ).order_by("-created_at")

    def reserved_total(self, card_id):
        total = Decimal("0")
        queryset = Invoice.objects.filter(card_id=card_id, status__in=OPEN_INVOICE_STATUSES)
        for invoice in queryset.only("amount", "paid_amount"):
            total += invoice.remaining_amount
        return total

    def public_paid(self, card_id):
        return (
            Payout.objects.filter(card_id=card_id, status__in=PUBLIC_PAYOUT_STATUSES)
            .select_related("invoice", "organization")
            .order_by("-processed_at", "-id")
        )

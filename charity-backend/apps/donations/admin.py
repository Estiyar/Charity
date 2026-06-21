from django.contrib import admin

from .models import Donation, RefundDecision


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "donor_name", "amount", "payment_status", "created_at")
    list_filter = ("payment_status",)


@admin.register(RefundDecision)
class RefundDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "card",
        "donor",
        "share_amount",
        "choice",
        "status",
        "deadline",
        "resolved_at",
    )
    list_filter = ("choice", "status")
    search_fields = ("donor__email", "donor__full_name", "card__full_name")

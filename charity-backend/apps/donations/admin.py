from django.contrib import admin
from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "donor_name", "amount", "payment_status", "created_at")
    list_filter = ("payment_status",)

from django.contrib import admin

from .models import BalanceTransaction, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "role", "status", "balance", "created_at")
    list_filter = ("role", "status")
    search_fields = ("full_name", "email", "phone")


@admin.register(BalanceTransaction)
class BalanceTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "transaction_type", "created_at")
    list_filter = ("transaction_type",)

from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "purpose", "amount", "status", "date")
    list_filter = ("status",)

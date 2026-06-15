from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "file_name", "file_type", "status", "has_confidential")
    list_filter = ("status", "file_type", "has_confidential")

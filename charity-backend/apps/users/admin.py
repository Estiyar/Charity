from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "role", "status", "created_at")
    list_filter = ("role", "status")
    search_fields = ("full_name", "email", "phone")

from django.contrib import admin
from .models import ModerationLog, RedistributionDecision


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "moderator", "action", "created_at")
    list_filter = ("action",)


@admin.register(RedistributionDecision)
class RedistributionDecisionAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "decision_type", "target_card", "created_by", "created_at")
    list_filter = ("decision_type",)

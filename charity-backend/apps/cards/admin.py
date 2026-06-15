from django.contrib import admin
from .models import FundraisingCard, City, Diagnosis


@admin.register(FundraisingCard)
class FundraisingCardAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "diagnosis", "city", "status",
                    "target_amount", "collected_amount", "end_date")
    list_filter = ("status", "city", "diagnosis")
    search_fields = ("full_name", "diagnosis", "city")


admin.site.register(City)
admin.site.register(Diagnosis)

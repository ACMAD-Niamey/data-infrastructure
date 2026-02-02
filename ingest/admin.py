from django.contrib import admin
from .models import APIKey, IngestionRun


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name", "key")
    list_filter = ("is_active",)


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ("dataset_id", "cadence", "status", "created_at")
    list_filter = ("status", "cadence")
    search_fields = ("dataset_id",)

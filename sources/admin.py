from django.contrib import admin

from .models import Policy, DataSource, Dataset


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner_org",
        "public_api_allowed",
        "dashboard_allowed",
        "internal_allowed",
        "partner_allowed",
    )
    list_filter = (
        "public_api_allowed",
        "dashboard_allowed",
        "internal_allowed",
        "partner_allowed",
        "raw_download_allowed",
        "aggregate_allowed",
        "station_visible",
    )
    search_fields = ("name", "owner_org")


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = (
        "source_code",
        "source_name",
        "source_type",
        "protocol",
        "is_active",
    )
    list_filter = ("source_type", "protocol", "is_active")
    search_fields = ("source_code", "source_name")


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "dataset_code",
        "dataset_name",
        "source",
        "policy",
        "variable_family",
        "temporal_resolution",
        "is_active",
    )
    list_filter = ("is_active", "source", "policy", "variable_family")
    search_fields = ("dataset_code", "dataset_name")
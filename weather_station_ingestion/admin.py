from django.contrib import admin

from weather_station_ingestion.models import IngestionJob, RawPayloadLog


@admin.register(RawPayloadLog)
class RawPayloadLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source_type",
        "source_identifier",
        "processing_status",
        "received_at",
    )
    list_filter = ("source_type", "processing_status")
    search_fields = ("source_identifier", "topic", "error_message")
    date_hierarchy = "received_at"


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job_type",
        "job_status",
        "source_name",
        "records_received",
        "records_processed",
        "records_failed",
        "created_at",
    )
    list_filter = ("job_type", "job_status")
    search_fields = ("source_name", "error_message")
    date_hierarchy = "created_at"
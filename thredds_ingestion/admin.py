from django.contrib import admin

from .models import DownloadRun, DownloadRunItem, DownloadWorkflow, DownloadWorkflowFile


class DownloadWorkflowFileInline(admin.TabularInline):
    model = DownloadWorkflowFile
    extra = 1
    fields = (
        "dataset",
        "label",
        "filename_pattern",
        "lead_hours_csv",
        "threshold_label",
        "item_id_pattern",
        "overwrite_existing",
        "enabled",
        "sort_order",
    )
    ordering = ("sort_order", "id")


@admin.register(DownloadWorkflow)
class DownloadWorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "schedule_hour_utc", "schedule_minute_utc", "updated_at")
    list_filter = ("enabled",)
    search_fields = ("name", "source_base_url")
    inlines = [DownloadWorkflowFileInline]


class DownloadRunItemInline(admin.TabularInline):
    model = DownloadRunItem
    extra = 0
    fields = ("workflow_file", "lead_hours", "filename", "status", "attempt_count", "item_id", "error_message")
    readonly_fields = fields
    can_delete = False


@admin.register(DownloadRun)
class DownloadRunAdmin(admin.ModelAdmin):
    list_display = (
        "workflow",
        "run_date",
        "status",
        "total_files",
        "completed_files",
        "failed_files",
        "not_yet_available_files",
    )
    list_filter = ("status", "workflow")
    date_hierarchy = "run_date"
    inlines = [DownloadRunItemInline]


@admin.register(DownloadRunItem)
class DownloadRunItemAdmin(admin.ModelAdmin):
    list_display = ("item_id", "run", "workflow_file", "lead_hours", "status", "attempt_count", "updated_at")
    list_filter = ("status",)
    search_fields = ("item_id", "filename", "error_message")

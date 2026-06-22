from django.contrib import admin
from catalog.models import ContactSubmission, FeedbackSubmission


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display  = ["project", "submitted_at"]
    list_filter   = ["project"]
    readonly_fields = ["project", "form_data", "submitted_at"]


@admin.register(FeedbackSubmission)
class FeedbackSubmissionAdmin(admin.ModelAdmin):
    list_display  = ["project", "submitted_at"]
    list_filter   = ["project"]
    readonly_fields = ["project", "form_data", "submitted_at"]

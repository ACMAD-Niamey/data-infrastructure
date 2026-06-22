from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from wagtail import hooks
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface
from wagtail.admin.viewsets.model import ModelViewSet

from catalog.models import ContactSubmission, FeedbackSubmission


class FeedbackSubmissionViewSet(ModelViewSet):
    model = FeedbackSubmission
    icon = "mail"
    menu_label = "Feedback"
    menu_name = "feedback_submissions"
    add_to_admin_menu = True
    list_display = ["__str__", "project", "submitted_at", "data_summary"]
    list_filter = ["project"]
    ordering = ["-submitted_at"]
    inspect_view_enabled = True
    inspect_view_fields = ["project", "submitted_at", "form_data"]
    panels = [
        FieldPanel("project", read_only=True),
        FieldPanel("submitted_at", read_only=True),
        FieldPanel("form_data", read_only=True),
    ]


class ContactSubmissionViewSet(ModelViewSet):
    model = ContactSubmission
    icon = "comment"
    menu_label = "Contact"
    menu_name = "contact_submissions"
    add_to_admin_menu = True
    list_display = ["__str__", "project", "submitted_at", "data_summary"]
    list_filter = ["project"]
    ordering = ["-submitted_at"]
    inspect_view_enabled = True
    inspect_view_fields = ["project", "submitted_at", "form_data"]
    panels = [
        FieldPanel("project", read_only=True),
        FieldPanel("submitted_at", read_only=True),
        FieldPanel("form_data", read_only=True),
    ]


@hooks.register("register_admin_viewset")
def register_feedback_submissions_viewset():
    return FeedbackSubmissionViewSet("feedback_submissions")


@hooks.register("register_admin_viewset")
def register_contact_submissions_viewset():
    return ContactSubmissionViewSet("contact_submissions")


@hooks.register("insert_global_admin_css")
def hex_color_admin_css():
    links = format_html(
        '<link rel="stylesheet" href="{}">',
        static("catalog/css/hex_color_widget.css"),
    ) + format_html(
        '<link rel="stylesheet" href="{}">',
        static("catalog/css/legend_map_widget.css"),
    )
    return mark_safe(links)


@hooks.register("insert_global_admin_js")
def catalog_admin_js():
    return mark_safe(
        format_html('<script src="{}"></script>', static("catalog/js/hex_color_widget.js"))
        + format_html('<script src="{}"></script>', static("catalog/js/legend_map_widget.js"))
    )


@hooks.register("insert_editor_js")
def catalog_editor_js():
    return mark_safe(
        format_html('<script src="{}"></script>', static("catalog/js/legend_map_widget.js"))
    )

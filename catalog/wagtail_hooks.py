from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from wagtail import hooks


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
def hex_color_admin_js():
    scripts = format_html(
        '<script src="{}"></script>',
        static("catalog/js/hex_color_widget.js"),
    ) + format_html(
        '<script src="{}"></script>',
        static("catalog/js/legend_map_widget.js"),
    )
    return mark_safe(scripts)

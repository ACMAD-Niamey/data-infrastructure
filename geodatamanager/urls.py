from django.conf import settings
from django.urls import include, path
from django.contrib import admin

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_patterns = [
    path("api/vector/", include("vector_ingest.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/ingest/", include("ingest.urls")),
    path("api/uploads/", include("uploads.urls")),
    path("api/observations/", include("observations.urls")),
]


urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(patterns=api_patterns), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path("api/django-admin/", admin.site.urls),
    path("api/admin/", include(wagtailadmin_urls)),
    path("api/documents/", include(wagtaildocs_urls)),
    path("api/search/", search_views.search, name="search"),
    path("api/catalog/", include("catalog.urls")),
    path("api/ingest/", include("ingest.urls")),
    path("api/vector/", include("vector_ingest.urls")),
    path("api/uploads/", include("uploads.urls")),
    path("api/observations/", include("observations.urls")),

   

]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("api/", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]

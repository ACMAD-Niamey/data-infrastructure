from django.urls import path
from .views import VectorIngestUploadView, VectorIngestStatusView

urlpatterns = [
    path("vector/ingest/", VectorIngestUploadView.as_view()),
    path("vector/ingest/<uuid:job_id>/status/", VectorIngestStatusView.as_view()),
]

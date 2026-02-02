from django.urls import path
from .api import IngestDatasetItemView

urlpatterns = [
    path("ingest/datasets/<slug:dataset_id>/items", IngestDatasetItemView.as_view(), name="ingest-dataset-item"),
]

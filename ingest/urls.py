from django.urls import path

from .api import IngestDatasetItemView
from .station_api import IngestStationTimeseriesView
from .delete_api import DeleteDatasetItemByDatetimeView, DeleteDatasetItemView

urlpatterns = [
    path(
        "ingest/datasets/<slug:dataset_id>/items/delete",
        DeleteDatasetItemByDatetimeView.as_view(),
        name="delete-dataset-item-by-datetime",
    ),
    path(
        "ingest/datasets/<slug:dataset_id>/items/<str:item_id>",
        DeleteDatasetItemView.as_view(),
        name="delete-dataset-item",
    ),
    path(
        "ingest/datasets/<slug:dataset_id>/stations",
        IngestStationTimeseriesView.as_view(),
        name="ingest-station-timeseries",
    ),
    path(
        "ingest/datasets/<slug:dataset_id>/items",
        IngestDatasetItemView.as_view(),
        name="ingest-dataset-item",
    ),
]

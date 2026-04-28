from django.urls import path
from stations.views import StationListView, StationDetailView, StationStatsView

urlpatterns = [
    path("", StationListView.as_view(), name="station-list"),
    path("<str:station_code>/", StationDetailView.as_view(), name="station-detail"),
    path("<str:station_code>/stats/", StationStatsView.as_view(), name="station-stats"),
]

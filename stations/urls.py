from django.urls import path
from stations.views import (
    CountryBoundsView,
    StationFacetsView,
    StationListView,
    StationDetailView,
    StationStatsView,
)

urlpatterns = [
    path("country-bounds/", CountryBoundsView.as_view(), name="country-bounds"),
    path("facets/", StationFacetsView.as_view(), name="station-facets"),
    path("", StationListView.as_view(), name="station-list"),
    path("<str:station_code>/", StationDetailView.as_view(), name="station-detail"),
    path("<str:station_code>/stats/", StationStatsView.as_view(), name="station-stats"),
]

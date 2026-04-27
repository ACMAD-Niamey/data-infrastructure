from django.urls import path

from observations.views import (
    LatestObservationsAPIView,
    ObservationStatsAPIView,
    StationObservationsAPIView,
    VariableObservationsAPIView,
)

urlpatterns = [
    path("latest/", LatestObservationsAPIView.as_view(), name="observations-latest"),
    path("stats/", ObservationStatsAPIView.as_view(), name="observations-stats"),
    path("station/<int:station_id>/", StationObservationsAPIView.as_view(), name="observations-by-station"),
    path("variable/<str:variable_code>/", VariableObservationsAPIView.as_view(), name="observations-by-variable"),
]

# from django.urls import path

# from .views import (
#     LatestObservationsAPIView,
#     ObservationStatsAPIView,
#     StationObservationsAPIView,
#     VariableObservationsAPIView,
# )

# urlpatterns = [
#     path("latest/", LatestObservationsAPIView.as_view(), name="observations-latest"),
#     path("stats/", ObservationStatsAPIView.as_view(), name="observations-stats"),
#     path("station/<int:station_id>/", StationObservationsAPIView.as_view(), name="observations-by-station"),
#     path("variable/<str:variable_code>/", VariableObservationsAPIView.as_view(), name="observations-by-variable"),
# ]
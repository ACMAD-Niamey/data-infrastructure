from django.urls import path, include
from rest_framework import routers
from .api import HazardCategoriesView, UILayersView, ProjectCountriesView, ProjectConfigView
from .views import DatasetAvailabilityView, DatasetVisualizationView

router = routers.DefaultRouter()

# router.register(r'datasets', DatasetAvailabilityView, basename='datasets')
# router.register(r'layers', UILayersView, basename='layers')

urlpatterns = [
    path('', include(router.urls)),
    path("ui/layers", UILayersView.as_view(), name="ui-layers"),
    path("hazard-categories/", HazardCategoriesView.as_view(), name="hazard-categories"),
    path("datasets/<str:dataset_id>/availability/", DatasetAvailabilityView.as_view(), 
         name="dataset-availability"),
    path("datasets/<str:dataset_id>/visualization/", DatasetVisualizationView.as_view(),
         name="dataset-visualization"),
    path("projects/<slug:slug>/countries/", ProjectCountriesView.as_view(), name="project-countries"),
    path("projects/<slug:slug>/config/", ProjectConfigView.as_view(), name="project-config"),
]

from django.urls import path, include
from rest_framework import routers
from .api import UILayersView
from .views import DatasetAvailabilityView

router = routers.DefaultRouter()

# router.register(r'datasets', DatasetAvailabilityView, basename='datasets')
# router.register(r'layers', UILayersView, basename='layers')

urlpatterns = [
    path('', include(router.urls)),
    path("ui/layers", UILayersView.as_view(), name="ui-layers"),
    path("datasets/<str:dataset_id>/availability/", DatasetAvailabilityView.as_view(), 
         name="dataset-availability"),
]

from django.urls import path
from .api import UILayersView

urlpatterns = [
    path("ui/layers", UILayersView.as_view(), name="ui-layers"),
]

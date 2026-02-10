from django.urls import path
from .views import PresignUploadView, DirectUpFileUploadView, UploadStatusView

urlpatterns = [
    path("presign", PresignUploadView.as_view(), name="uploads-presign"),
    path("direct", DirectUpFileUploadView.as_view(), name="uploads-direct"),
    path("status/<str:task_id>", UploadStatusView.as_view(), name="uploads-status"),
]

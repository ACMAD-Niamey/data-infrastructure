from rest_framework import serializers

class PresignUploadRequestSerializer(serializers.Serializer):
    dataset_id = serializers.CharField(max_length=128)
    filename = serializers.CharField(max_length=512)
    content_type = serializers.CharField(max_length=255, required=False, allow_blank=True)

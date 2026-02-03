from rest_framework import serializers
from .models import VectorIngestJob
from .utils import normalize_table_name

class VectorIngestCreateSerializer(serializers.ModelSerializer):
    upload = serializers.FileField(write_only=True)
    class Meta:
        model = VectorIngestJob
        fields = ["id", "dataset_name", "table_name", "srid", "upload"]
        read_only_fields = ["id"]

    def validate_table_name(self, v):
        return normalize_table_name(v)

class VectorIngestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorIngestJob
        fields = [
            "id","dataset_name","schema_name","table_name","srid",
            "ingest_status","ingest_error","archive_status","archive_error",
            "archive_uri","row_count","created_at","updated_at"
        ]

from rest_framework import serializers


class STACAssetSerializer(serializers.Serializer):
    """STAC Asset for ingestion"""
    href = serializers.CharField(
        required=True,
        help_text="S3 URI pointing to the file in MinIO (e.g., s3://geodata/trees/2025/12/file.tif)"
    )
    roles = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Asset roles (e.g., ['data'])"
    )
    type = serializers.CharField(
        required=False,
        help_text="MIME type of the asset"
    )


class IngestRequestSerializer(serializers.Serializer):
    """Request payload for ingesting a dataset item into STAC"""
    
    asset = STACAssetSerializer(
        required=True,
        help_text="Asset metadata including the S3 URI where the file is stored"
    )
    
    # For daily/monthly cadence
    datetime = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="ISO 8601 datetime for single-timestamp data (required for daily/monthly cadence)"
    )
    
    # For dekadal/seasonal cadence
    start_datetime = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Start datetime for time-range data (required for dekadal/seasonal cadence)"
    )
    end_datetime = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="End datetime for time-range data (required for dekadal/seasonal cadence)"
    )
    
    bbox = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        allow_null=True,
        help_text="Bounding box [west, south, east, north]"
    )
    
    geometry = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="GeoJSON geometry object"
    )
    
    item_id = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Optional custom STAC item ID. If not provided, will be auto-generated."
    )
    
    stac_item = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Complete STAC item JSON. If provided, other fields are ignored."
    )


class IngestResponseSerializer(serializers.Serializer):
    """Response from ingestion request"""
    run_id = serializers.IntegerField(
        help_text="ID of the ingestion run for tracking"
    )
    status = serializers.CharField(
        help_text="Current status of the ingestion run (e.g., 'accepted')"
    )


class DeleteByDatetimeSerializer(serializers.Serializer):
    """Identify a STAC item to delete by temporal fields (same rules as ingest)."""

    datetime = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Required for daily/monthly cadence (same as ingest)",
    )
    start_datetime = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Required for dekadal/seasonal cadence",
    )
    end_datetime = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Required for dekadal/seasonal cadence",
    )
    item_id = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Optional explicit STAC item id (skips STAC search)",
    )


class DeleteResponseSerializer(serializers.Serializer):
    """Response from delete request (async deletion run)."""

    run_id = serializers.IntegerField(help_text="ID of the deletion run for tracking")
    status = serializers.CharField(help_text="Current status (e.g. accepted)")
    item_id = serializers.CharField(
        required=False,
        help_text="STAC item id that will be deleted",
    )
    delete_object = serializers.BooleanField(
        help_text="Whether the MinIO raster will also be removed",
    )

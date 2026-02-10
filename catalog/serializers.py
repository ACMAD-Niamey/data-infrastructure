from rest_framework import serializers


class DatasetSerializer(serializers.Serializer):
    """Dataset metadata serializer"""
    id = serializers.CharField(max_length=80)
    title = serializers.CharField(max_length=255)
    cadence = serializers.ChoiceField(choices=["daily", "dekadal", "monthly", "seasonal"])
    dataset_type = serializers.ChoiceField(choices=["raster", "vector"])
    stac_collection = serializers.CharField(max_length=120)


class TileConfigSerializer(serializers.Serializer):
    """Tile configuration serializer"""
    template = serializers.CharField(max_length=300)
    params = serializers.JSONField()


class UIConfigSerializer(serializers.Serializer):
    """UI display configuration serializer"""
    default_visible = serializers.BooleanField()
    opacity = serializers.FloatField(min_value=0.0, max_value=1.0)
    minzoom = serializers.IntegerField(min_value=0)
    maxzoom = serializers.IntegerField(min_value=0, max_value=22)


class LayerSerializer(serializers.Serializer):
    """Complete layer configuration serializer"""
    id = serializers.CharField(max_length=120)
    title = serializers.CharField(max_length=120)
    type = serializers.ChoiceField(choices=["raster", "vector"])
    project = serializers.CharField(max_length=255, allow_null=True)
    dataset = DatasetSerializer()
    tile = TileConfigSerializer()
    ui = UIConfigSerializer()
    legend = serializers.JSONField()
    updated_at = serializers.DateTimeField()


class UILayersResponseSerializer(serializers.Serializer):
    """Response serializer for UI layers endpoint"""
    version = serializers.CharField(max_length=10)
    layers = LayerSerializer(many=True)


class DatasetAvailabilityRequestSerializer(serializers.Serializer):
    """Request serializer for dataset availability"""
    cadence = serializers.ChoiceField(
        choices=["daily", "dekadal", "monthly"],
        required=False,
        default="daily",
        help_text="Temporal cadence to aggregate availability"
    )


class DatasetAvailabilityResponseSerializer(serializers.Serializer):
    """Response serializer for dataset availability"""
    dataset_id = serializers.CharField(max_length=80)
    cadence = serializers.CharField(max_length=10)
    available = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of available dates in ISO format"
    )
    min = serializers.DateField(
        allow_null=True,
        help_text="Earliest available date"
    )
    max = serializers.DateField(
        allow_null=True,
        help_text="Latest available date"
    )

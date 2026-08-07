from rest_framework import serializers
import re


class YearMonthOrDateField(serializers.CharField):
    """Accept YYYY-MM or YYYY-MM-DD strings."""

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", value):
            raise serializers.ValidationError(
                "Date must be in YYYY, YYYY-MM, or YYYY-MM-DD format."
            )
        return value


class DatasetSerializer(serializers.Serializer):
    """Dataset metadata serializer"""
    id = serializers.CharField(max_length=80)
    title = serializers.CharField(max_length=255)
    cadence = serializers.ChoiceField(choices=["daily", "dekadal", "monthly", "seasonal", "annual"])
    dataset_type = serializers.ChoiceField(choices=["raster", "vector"])
    stac_collection = serializers.CharField(max_length=120)


class TileConfigSerializer(serializers.Serializer):
    """Tile configuration serializer"""
    template = serializers.CharField(max_length=300)
    params = serializers.JSONField()


class UIConfigSerializer(serializers.Serializer):
    """UI display configuration serializer"""
    default_visible = serializers.BooleanField()
    always_on_top = serializers.BooleanField(required=False, default=False)
    opacity = serializers.FloatField(min_value=0.0, max_value=1.0)
    minzoom = serializers.IntegerField(min_value=0)
    maxzoom = serializers.IntegerField(min_value=0, max_value=22)
    color_class = serializers.CharField(max_length=80, required=False)


class DescriptionSerializer(serializers.Serializer):
    html = serializers.CharField()
    plain = serializers.CharField()


class IconSerializer(serializers.Serializer):
    slug = serializers.CharField(max_length=80)
    url = serializers.URLField()


class SelectionSerializer(serializers.Serializer):
    cadence = serializers.ChoiceField(
        choices=["daily", "dekadal", "monthly", "seasonal", "annual"]
    )


class LayerSerializer(serializers.Serializer):
    """Complete layer configuration serializer"""
    id = serializers.CharField(max_length=120)
    title = serializers.CharField(max_length=120)
    type = serializers.ChoiceField(choices=["raster", "vector"])
    project = serializers.CharField(max_length=255, allow_null=True, required=False)
    description = DescriptionSerializer()
    icon = IconSerializer(allow_null=True)
    dataset = DatasetSerializer()
    selection = SelectionSerializer()
    tile = TileConfigSerializer()
    ui = UIConfigSerializer()
    legend = serializers.JSONField()
    updated_at = serializers.DateTimeField()


class UILayersResponseSerializer(serializers.Serializer):
    """Response serializer for UI layers endpoint"""
    version = serializers.CharField(max_length=10)
    project = serializers.CharField(max_length=255)
    layers = LayerSerializer(many=True)


class DatasetAvailabilityRequestSerializer(serializers.Serializer):
    """Request serializer for dataset availability"""
    cadence = serializers.ChoiceField(
        choices=["daily", "dekadal", "monthly", "annual"],
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


class DatasetVisualizationRequestSerializer(serializers.Serializer):
    """Request serializer for dataset visualization parameters"""
    date = YearMonthOrDateField(
        required=True,
        help_text="Specific date to visualize (YYYY-MM or YYYY-MM-DD)"
    )
    cadence = serializers.ChoiceField(
        choices=["daily", "dekadal", "monthly", "annual"],
        required=True,
        help_text="Temporal cadence for visualization"
    )

class DatasetVisualizationResponseSerializer(serializers.Serializer):
    """Response serializer for dataset visualization parameters"""
    dataset_id = serializers.CharField(max_length=80)
    cadence = serializers.CharField(max_length=10)
    titiler_url = serializers.URLField(
        help_text="URL to the titiler endpoint for visualizing this dataset"
    )
    titiler_info = serializers.JSONField(
        help_text="Additional info from titiler for visualization"
    )
    legend = serializers.JSONField(
        help_text="Legend configuration for visualizing this dataset"
    )
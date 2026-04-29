from rest_framework import serializers


class ObservationRecordSerializer(serializers.Serializer):
    station_id = serializers.IntegerField()
    sensor_id = serializers.IntegerField(allow_null=True)
    dataset_id = serializers.IntegerField()
    source_id = serializers.IntegerField()
    observed_at = serializers.DateTimeField()
    variable_code = serializers.CharField()
    raw_value = serializers.FloatField(allow_null=True)
    cleaned_value = serializers.FloatField(allow_null=True)
    unit = serializers.CharField(allow_null=True)
    qc_flag = serializers.CharField()
    qc_notes = serializers.CharField(allow_null=True)
    ingest_time = serializers.DateTimeField()
    payload_ref = serializers.CharField(allow_null=True)


class VariableCountSerializer(serializers.Serializer):
    variable_code = serializers.CharField()
    count = serializers.IntegerField()


class ObservationStatsSerializer(serializers.Serializer):
    total_count = serializers.IntegerField()
    latest_timestamp = serializers.DateTimeField(allow_null=True)
    by_variable = VariableCountSerializer(many=True)


# ---------------------------------------------------------------------------
# Station stats API serializers
# ---------------------------------------------------------------------------

class VariableSummarySerializer(serializers.Serializer):
    variable_code = serializers.CharField()
    unit = serializers.CharField(allow_null=True)
    record_count = serializers.IntegerField()
    first_observation = serializers.DateTimeField(allow_null=True)
    last_observation = serializers.DateTimeField(allow_null=True)


class StationInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    station_code = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    country_code = serializers.CharField(allow_null=True)
    country_name = serializers.CharField(allow_null=True, required=False)
    station_type = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()
    elevation_m = serializers.FloatField(allow_null=True)
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)
    total_records = serializers.IntegerField()
    first_observation = serializers.DateTimeField(allow_null=True)
    last_observation = serializers.DateTimeField(allow_null=True)
    variables = VariableSummarySerializer(many=True)


class StationListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    station_code = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    country_code = serializers.CharField(allow_null=True)
    country_name = serializers.CharField(allow_null=True, required=False)
    admin1 = serializers.CharField(allow_null=True, required=False)
    admin2 = serializers.CharField(allow_null=True, required=False)
    station_type = serializers.CharField(allow_null=True)
    elevation_m = serializers.FloatField(allow_null=True)
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)
    variables_available = serializers.ListField(child=serializers.CharField())
    latest_observed_at = serializers.DateTimeField(allow_null=True)


class SpatialExtentSerializer(serializers.Serializer):
    west = serializers.FloatField()
    south = serializers.FloatField()
    east = serializers.FloatField()
    north = serializers.FloatField()


class StationListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = StationListItemSerializer(many=True)
    extent = SpatialExtentSerializer(allow_null=True)


class FacetOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class CountryBoundsOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    bounds = SpatialExtentSerializer()


class StationFacetsSerializer(serializers.Serializer):
    countries = FacetOptionSerializer(many=True)
    admin1 = serializers.ListField(child=serializers.CharField())


class TimeSeriesRawBucketSerializer(serializers.Serializer):
    period = serializers.DateTimeField()
    value = serializers.FloatField(allow_null=True)
    unit = serializers.CharField(allow_null=True)


class TimeSeriesAggBucketSerializer(serializers.Serializer):
    period = serializers.DateTimeField()
    avg = serializers.FloatField(allow_null=True)
    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
    count = serializers.IntegerField()


class StationStatsResponseSerializer(serializers.Serializer):
    station_code = serializers.CharField()
    station_name = serializers.CharField(allow_null=True)
    variable = serializers.CharField()
    aggregation = serializers.CharField()
    start = serializers.CharField()
    end = serializers.CharField()
    data = serializers.ListField()

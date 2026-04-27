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
from datetime import datetime, date, time, timezone

from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import serializers


class DateOrDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=timezone.utc)
        if isinstance(value, str):
            parsed_datetime = parse_datetime(value)
            if parsed_datetime:
                if parsed_datetime.tzinfo is None:
                    parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
                return parsed_datetime
            parsed_date = parse_date(value)
            if parsed_date:
                return datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
        return super().to_internal_value(value)

class PresignUploadRequestSerializer(serializers.Serializer):
    dataset_id = serializers.CharField(max_length=128)
    filename = serializers.CharField(max_length=512)
    content_type = serializers.CharField(max_length=255, required=False, allow_blank=True)

class PresignUploadResponseSerializer(serializers.Serializer):
    dataset_id = serializers.CharField(max_length=128)
    bucket = serializers.CharField(max_length=128)
    key = serializers.CharField(max_length=512)
    href = serializers.CharField(max_length=512)
    upload_url = serializers.URLField()
    expires_in = serializers.IntegerField()
    content_type = serializers.CharField(max_length=255)


class DirectUploadRequestSerializer(serializers.Serializer):
    dataset_id = serializers.CharField(max_length=128)
    file = serializers.FileField()
    bucket = serializers.CharField(max_length=128, required=False, allow_blank=True)
    auto_extract = serializers.BooleanField(required=False, default=True)
    auto_ingest = serializers.BooleanField(required=False, default=False)
    item_id = serializers.CharField(max_length=160, required=False, allow_blank=True)
    datetime = DateOrDateTimeField(required=False)
    start_datetime = DateOrDateTimeField(required=False)
    end_datetime = DateOrDateTimeField(required=False)
    bbox = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        min_length=4,
        max_length=4,
    )
    geometry = serializers.JSONField(required=False)
    stac_item = serializers.JSONField(required=False)


class DirectUploadResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField(max_length=255)
    dataset_id = serializers.CharField(max_length=128)
    bucket = serializers.CharField(max_length=128)
    key = serializers.CharField(max_length=512)
    status = serializers.CharField(max_length=50)
    status_url = serializers.URLField()
    auto_ingest = serializers.BooleanField()
    message = serializers.CharField(max_length=255)


class UploadStatusResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["pending", "processing", "completed", "failed"])
    bucket = serializers.CharField(max_length=128, required=False)
    key = serializers.CharField(max_length=512, required=False)
    href = serializers.CharField(max_length=512, required=False)
    size = serializers.IntegerField(required=False)
    content_type = serializers.CharField(max_length=255, required=False)
    auto_ingest = serializers.BooleanField(required=False)
    ingest_status = serializers.CharField(max_length=50, required=False)
    ingest_run_id = serializers.IntegerField(required=False)
    ingest_error = serializers.CharField(max_length=1024, required=False, allow_null=True)
    error = serializers.CharField(max_length=1024, required=False, allow_null=True)

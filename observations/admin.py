from django.contrib import admin

from .models import Observation, StationHealth


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = (
        "station",
        "variable_code",
        "observed_at",
        "cleaned_value",
        "unit",
        "qc_flag",
        "dataset",
        "source",
    )
    list_filter = ("variable_code", "qc_flag", "dataset", "source")
    search_fields = ("station__station_code", "station__name", "payload_ref")
    date_hierarchy = "observed_at"


@admin.register(StationHealth)
class StationHealthAdmin(admin.ModelAdmin):
    list_display = (
        "station",
        "observed_at",
        "battery_voltage",
        "signal_strength",
        "health_status",
    )
    list_filter = ("health_status",)
    search_fields = ("station__station_code", "station__name")
    date_hierarchy = "observed_at"
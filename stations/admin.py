from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Station, StationAlias, StationSensor


class StationAliasInline(admin.TabularInline):
    model = StationAlias
    extra = 1


class StationSensorInline(admin.TabularInline):
    model = StationSensor
    extra = 1


@admin.register(Station)
class StationAdmin(GISModelAdmin):
    list_display = (
        "station_code",
        "name",
        "wmo_id",
        "country_code",
        "station_type",
        "agency",
        "is_active",
    )
    list_filter = ("station_type", "country_code", "is_active", "agency")
    search_fields = ("station_code", "name", "wmo_id", "agency")
    inlines = [StationAliasInline, StationSensorInline]


@admin.register(StationAlias)
class StationAliasAdmin(admin.ModelAdmin):
    list_display = ("station", "source_name", "alias_code", "alias_name")
    list_filter = ("source_name",)
    search_fields = ("alias_code", "alias_name", "station__name", "station__station_code")


@admin.register(StationSensor)
class StationSensorAdmin(admin.ModelAdmin):
    list_display = ("station", "sensor_code", "variable_code", "unit", "status")
    list_filter = ("variable_code", "status")
    search_fields = ("sensor_code", "station__name", "station__station_code")
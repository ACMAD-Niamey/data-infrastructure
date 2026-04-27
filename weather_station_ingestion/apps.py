from django.apps import AppConfig


class WeatherStationIngestionConfig(AppConfig):
    name = "weather_station_ingestion"
    label = "ingestion"  # keep DB tables & migrations unchanged

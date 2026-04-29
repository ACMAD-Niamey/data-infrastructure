from __future__ import annotations

from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import TestCase

from stations.models import Station
from stations.services.station_geography_enricher import StationGeographyEnricher


class StationGeographyEnricherTests(TestCase):
    def _make_station(self, **kwargs) -> Station:
        defaults = {
            "station_code": "TST001",
            "name": "Test Station",
            "country_code": "KEN",
            "geom": Point(36.8219, -1.2921, srid=4326),
            "station_type": Station.StationType.AWS,
            "is_active": True,
        }
        defaults.update(kwargs)
        return Station.objects.create(**defaults)

    def test_iso_mapping_fills_country_name_when_reverse_geocode_fails(self):
        station = self._make_station(country_name=None)
        enricher = StationGeographyEnricher(throttle_s=0)

        with patch.object(enricher, "_reverse_geocode", return_value=None) as reverse:
            result = enricher.enrich_station_geography(station)

        reverse.assert_called_once()
        self.assertEqual(result["country_name"], "Kenya")
        station.refresh_from_db()
        self.assertEqual(station.country_name, "Kenya")

    def test_reverse_geocode_fallback_fills_missing_fields(self):
        station = self._make_station(country_code=None, country_name=None, admin1=None, admin2=None)
        enricher = StationGeographyEnricher(throttle_s=0)

        payload = {
            "address": {
                "country": "Rwanda",
                "state": "Kigali City",
                "county": "Gasabo",
            }
        }
        with patch.object(enricher, "_reverse_geocode", return_value=payload):
            result = enricher.enrich_station_geography(station)

        self.assertEqual(result["country_name"], "Rwanda")
        self.assertEqual(result["admin1"], "Kigali City")
        self.assertEqual(result["admin2"], "Gasabo")
        station.refresh_from_db()
        self.assertEqual(station.country_name, "Rwanda")
        self.assertEqual(station.admin1, "Kigali City")
        self.assertEqual(station.admin2, "Gasabo")

    def test_dry_run_does_not_persist(self):
        station = self._make_station(country_name=None)
        enricher = StationGeographyEnricher(throttle_s=0)
        with patch.object(enricher, "_reverse_geocode", return_value=None):
            result = enricher.enrich_station_geography(station, persist=False)
        self.assertEqual(result["country_name"], "Kenya")
        station.refresh_from_db()
        self.assertIsNone(station.country_name)

    def test_normalizes_whitespace_and_unicode(self):
        station = self._make_station(country_name="  KENYA  ", admin1=None, admin2=None)
        enricher = StationGeographyEnricher(throttle_s=0)
        payload = {"address": {"state": "  K\u2019iambu   County  ", "county": "  Kiambu  "}}

        with patch.object(enricher, "_reverse_geocode", return_value=payload):
            result = enricher.enrich_station_geography(station)

        self.assertEqual(result["admin1"], "K’iambu County")
        self.assertEqual(result["admin2"], "Kiambu")


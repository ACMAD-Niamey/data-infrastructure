"""Tests for station time-series ingestion, the series API and value visibility."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from wagtail.models import Page

from catalog.models import DatasetPage, ProjectPage
from ingest.models import APIKey, IngestionRun
from ingest.station_timeseries.filename import parse_sensor_filename
from ingest.station_timeseries.geocoder import NominatimGeocoder
from ingest.station_timeseries.parser import parse_sensor_csv
from ingest.station_timeseries.service import (
    NoDeploymentFixError,
    StationTimeseriesIngestService,
)
from observations.models import Observation
from stations.models import Station
from stations.services.value_visibility import allowed_values

HEADER = (
    "timestamp_utc;time_source;lat;lon;alt_m;sats;hdop;dht_temp_c;dht_rh_pct;"
    "ds18b20_temp_c;lux;batt_v;phase"
)
BELGIUM_FIX = "2026-01-01T10:00:00Z;GPS;50.9066;4.4711;0;4;3.9;;;;;3.8;GPS20x"
NIAMEY_FIX = "2026-05-18T11:00:00Z;GPS;13.5153;2.1040;220;7;1.0;;;;;4.1;GPS20x"
NIAMEY_FIX_2 = "2026-05-18T11:00:10Z;GPS;13.5155;2.1042;218;7;1.0;;;;;4.1;GPS20x"
BENCH_ROW = "2026-01-01T10:05:00Z;RTC;;;;;;21.0;40.0;21.5;100;3.8;MIN1"
ROW_1 = "2026-05-18T11:05:00Z;RTC;;;;;;40.1;30.2;45.3;50000;4.0;MIN1"
ROW_2 = "2026-05-18T11:06:00Z;RTC;;;;;;40.3;;45.9;-1;4.0;MIN1"  # empty rh, lux sentinel


class _FakeGeocoder:
    def __init__(self, name: str | None = "Plateau, Niamey") -> None:
        self.name = name
        self.calls = 0

    def place_name(self, lat: float, lon: float) -> str | None:
        self.calls += 1
        return self.name


def _write_csv(directory: str, name: str, lines: list[str]) -> Path:
    path = Path(directory) / name
    path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8")
    return path


class FilenameTests(TestCase):
    def test_reads_number_and_exposure(self):
        identity = parse_sensor_filename("Capteur 002 Soleil.CSV")
        self.assertEqual(identity.station_code, "CAPTEUR-002")
        self.assertEqual(identity.exposure, "sun")

    def test_parenthesised_label_and_padding(self):
        identity = parse_sensor_filename("Capteur 4 (Ombre).csv")
        self.assertEqual(identity.station_code, "CAPTEUR-004")
        self.assertEqual(identity.exposure, "shade")

    def test_missing_exposure_is_none(self):
        self.assertIsNone(parse_sensor_filename("Capteur 010.CSV").exposure)

    def test_no_number_raises(self):
        with self.assertRaises(ValueError):
            parse_sensor_filename("readme.csv")


class ParserTests(TestCase):
    def test_splits_phases_and_counts_bad_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_csv(tmp, "c.csv", [
                NIAMEY_FIX, ROW_1, ROW_2,
                "not-a-date;RTC;;;;;;1;1;1;1;1;MIN1",
                "2026-05-18T11:07:00Z;RTC;;;;;;1;1;1;1;1;WEIRD",
            ])
            parsed = parse_sensor_csv(path)
        self.assertEqual(len(parsed.gps_fixes), 1)
        self.assertEqual(len(parsed.measurements), 2)
        self.assertEqual(parsed.skipped_rows, 2)
        self.assertIsNone(parsed.measurements[1].values["dht_rh_pct"])


class ServiceTests(TestCase):
    def _ingest(self, lines, name="Capteur 006 Ombre.CSV", geocoder=None, **kwargs):
        service = StationTimeseriesIngestService(geocoder=geocoder or _FakeGeocoder())
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_csv(tmp, name, lines)
            return service.ingest_file(
                path, dataset_id="heat-niamey", dataset_title="Heat Niamey",
                context={"group": "Groupe 1", "commune": "Commune 5"}, **kwargs,
            )

    def test_skips_pre_deployment_rows(self):
        summary = self._ingest([BELGIUM_FIX, BENCH_ROW, NIAMEY_FIX, ROW_1])
        self.assertEqual(summary.rows_before_deployment, 1)
        times = set(
            Observation.objects.filter(station__station_code="CAPTEUR-006")
            .values_list("observed_at", flat=True)
        )
        self.assertEqual(len(times), 1)

    def test_writes_raw_only_and_keeps_values_as_logged(self):
        self._ingest([NIAMEY_FIX, ROW_1, ROW_2])
        # values_list: the unmanaged Observation table has no `id` column.
        raw, cleaned, qc = Observation.objects.filter(
            station__station_code="CAPTEUR-006", variable_code="lux",
            observed_at="2026-05-18T11:06:00Z",
        ).values_list("raw_value", "cleaned_value", "qc_flag").get()
        self.assertEqual(raw, -1)  # sentinel kept; cleaning is deferred
        self.assertIsNone(cleaned)
        self.assertEqual(qc, "unchecked")

    def test_empty_channel_writes_no_row(self):
        self._ingest([NIAMEY_FIX, ROW_2])
        self.assertFalse(
            Observation.objects.filter(variable_code="rh", station__station_code="CAPTEUR-006").exists()
        )

    def test_station_metadata_and_position(self):
        self._ingest([NIAMEY_FIX, NIAMEY_FIX_2, ROW_1], name="Capteur 018 Soleil.CSV")
        station = Station.objects.get(station_code="CAPTEUR-018")
        self.assertEqual(station.metadata_json["exposure"], "sun")
        self.assertEqual(station.metadata_json["dataset_code"], "heat-niamey")
        self.assertEqual(station.metadata_json["commune"], "Commune 5")
        self.assertIn("Plateau", station.name)
        self.assertAlmostEqual(station.geom.y, 13.5154, places=4)  # median of two fixes
        self.assertTrue(station.has_observations)
        self.assertEqual(station.sensors.count(), 5)

    def test_reload_is_idempotent_and_geocodes_once(self):
        geocoder = _FakeGeocoder()
        self._ingest([NIAMEY_FIX, ROW_1], geocoder=geocoder)
        self._ingest([NIAMEY_FIX, ROW_1], geocoder=geocoder)
        self.assertEqual(
            Observation.objects.filter(station__station_code="CAPTEUR-006", variable_code="temp").count(), 1
        )
        self.assertEqual(geocoder.calls, 1)

    def test_geocoder_failure_falls_back_to_generic_name(self):
        self._ingest([NIAMEY_FIX, ROW_1], geocoder=_FakeGeocoder(name=None))
        self.assertTrue(Station.objects.get(station_code="CAPTEUR-006").name.startswith("Niamey"))

    def test_file_with_only_foreign_fixes_is_rejected(self):
        with self.assertRaises(NoDeploymentFixError):
            self._ingest([BELGIUM_FIX, BENCH_ROW])


class NominatimNameTests(TestCase):
    def test_prefers_neighbourhood_with_city(self):
        name = NominatimGeocoder.name_from_address({"suburb": "Plateau", "city": "Niamey"})
        self.assertEqual(name, "Plateau, Niamey")

    def test_city_only(self):
        self.assertEqual(NominatimGeocoder.name_from_address({"city": "Niamey"}), "Niamey")

    def test_empty_address(self):
        self.assertIsNone(NominatimGeocoder.name_from_address({}))


class VisibilityAndApiTests(TestCase):
    def setUp(self):
        root = Page.get_first_root_node()
        project = root.add_child(instance=ProjectPage(title="P", slug="p-ts"))
        self.page = DatasetPage(
            title="Heat Niamey", slug="heat-niamey", dataset_id="heat-niamey",
            dataset_type="station_timeseries", cadence="daily",
        )
        project.add_child(instance=self.page)
        service = StationTimeseriesIngestService(geocoder=_FakeGeocoder())
        with tempfile.TemporaryDirectory() as tmp:
            service.ingest_file(
                _write_csv(tmp, "Capteur 006 Ombre.CSV", [NIAMEY_FIX, ROW_1, ROW_2]),
                dataset_id="heat-niamey", dataset_title="Heat Niamey", context={},
            )
        self.client = APIClient()

    def _series(self, **params):
        query = {"variable": "temp", "agg": "raw", "start": "2026-05-18", "end": "2026-05-18", **params}
        return self.client.get("/api/stations/CAPTEUR-006/stats/", query)

    def test_default_exposes_raw_only(self):
        self.assertEqual(allowed_values("CAPTEUR-006"), ["raw"])
        response = self._series()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["available_values"], ["raw"])

    def test_cleaned_is_forbidden_until_enabled(self):
        response = self._series(value="cleaned")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["available_values"], ["raw"])

    def test_cleaned_enabled_but_empty_returns_no_rows(self):
        self.page.show_cleaned_values = True
        self.page.save()
        response = self._series(value="cleaned")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], [])

    def test_raw_can_be_hidden(self):
        self.page.show_raw_values = False
        self.page.save()
        self.assertEqual(self._series().status_code, 403)

    def test_invalid_value_is_400(self):
        self.assertEqual(self._series(value="bogus").status_code, 400)

    def test_non_dataset_station_stays_raw_only(self):
        Station.objects.filter(station_code="CAPTEUR-006").update(metadata_json=None)
        self.assertEqual(allowed_values("CAPTEUR-006"), ["raw"])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class UploadApiTests(TestCase):
    def setUp(self):
        root = Page.get_first_root_node()
        project = root.add_child(instance=ProjectPage(title="P", slug="p-up"))
        project.add_child(instance=DatasetPage(
            title="Heat", slug="heat-up", dataset_id="heat-up",
            dataset_type="station_timeseries", cadence="daily",
        ))
        project.add_child(instance=DatasetPage(
            title="Raster", slug="rast-up", dataset_id="rast-up",
            dataset_type="raster", cadence="daily",
        ))
        self.key = APIKey.objects.create(name="t")
        self.client = APIClient()
        self.client.credentials(HTTP_X_API_KEY=self.key.key)

    def _post(self, dataset_id, files=None):
        data = {"files": files} if files else {}
        return self.client.post(
            f"/api/ingest/ingest/datasets/{dataset_id}/stations", data, format="multipart"
        )

    def _file(self):
        return SimpleUploadedFile("Capteur 007 Soleil.CSV", f"{HEADER}\n{NIAMEY_FIX}\n".encode())

    def test_requires_auth(self):
        response = APIClient().post("/api/ingest/ingest/datasets/heat-up/stations")
        self.assertIn(response.status_code, (401, 403))

    def test_unknown_dataset_404(self):
        self.assertEqual(self._post("nope", [self._file()]).status_code, 404)

    def test_wrong_dataset_type_400(self):
        self.assertEqual(self._post("rast-up", [self._file()]).status_code, 400)

    def test_no_files_400(self):
        self.assertEqual(self._post("heat-up").status_code, 400)

    @patch("ingest.tasks.process_station_timeseries_run.delay")
    def test_accepts_files_and_queues_run(self, delay):
        response = self._post("heat-up", [self._file()])
        self.assertEqual(response.status_code, 202)
        run = IngestionRun.objects.get(id=response.json()["run_id"])
        self.assertEqual(run.payload["kind"], "station_timeseries")
        self.assertTrue(Path(run.payload["files"][0]).exists())
        delay.assert_called_once_with(run.id)

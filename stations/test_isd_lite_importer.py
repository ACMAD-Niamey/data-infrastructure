from __future__ import annotations

from datetime import datetime, timezone

from django.test import SimpleTestCase

from stations.services.isd_lite_importer import VARIABLE_MAP, parse_lines


class IsdLiteParserTests(SimpleTestCase):
    SAMPLE = (
        # year mo dy hr  temp dewp  slp wdir wspd skyc prcp_1h prcp_6h
        "2023 01 01 00   234   12 10211   90   25    8     -1   -9999\n"
        "2023 01 01 01 -9999 -9999 10215 -9999 -9999    8     50   -9999\n"
        "2023 01 01 02   240   13 10210  100   30    8      0   -9999\n"
        "\n"
        "garbage line that should be ignored\n"
    )

    def test_yields_only_mapped_variables(self):
        codes = {row[1] for row in parse_lines(self.SAMPLE)}
        self.assertEqual(codes, {code for code, _, _ in VARIABLE_MAP.values()})

    def test_drops_missing_values(self):
        rows = list(parse_lines(self.SAMPLE))
        # Hour 1 has -9999 in temp / wdir / wspd; only pressure and rainfall stay.
        hour_1 = [r for r in rows if r[0].hour == 1]
        codes = sorted(r[1] for r in hour_1)
        self.assertEqual(codes, ["pressure", "rainfall"])

    def test_trace_precip_normalized_to_zero(self):
        rows = list(parse_lines(self.SAMPLE))
        rainfall_h0 = [r for r in rows if r[0].hour == 0 and r[1] == "rainfall"]
        self.assertEqual(len(rainfall_h0), 1)
        self.assertEqual(rainfall_h0[0][2], 0.0)

    def test_scaling_and_units(self):
        rows = list(parse_lines(self.SAMPLE))
        by_code_hour: dict[tuple[str, int], tuple[float, str]] = {
            (code, ts.hour): (value, unit) for ts, code, value, unit in rows
        }
        self.assertEqual(by_code_hour[("temp", 0)], (23.4, "degC"))
        self.assertEqual(by_code_hour[("pressure", 0)], (1021.1, "hPa"))
        self.assertEqual(by_code_hour[("wind_direction", 0)], (90.0, "deg"))
        self.assertEqual(by_code_hour[("wind_speed", 0)], (2.5, "m/s"))
        self.assertEqual(by_code_hour[("rainfall", 1)], (5.0, "mm"))

    def test_timestamps_are_utc_aware(self):
        rows = list(parse_lines(self.SAMPLE))
        for ts, *_ in rows:
            self.assertIsInstance(ts, datetime)
            self.assertEqual(ts.tzinfo, timezone.utc)

    def test_rejects_short_or_invalid_lines(self):
        bad = "2023 01 01\n2023 13 40 99 10 10 10 10 10 10 10 10\n"
        rows = list(parse_lines(bad))
        self.assertEqual(rows, [])

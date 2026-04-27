from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from weather_station_ingestion.services.parser_registry import ParserRegistry


@dataclass
class ExtractedStationObservation:
    source_name: str | None
    wmo_id: str | None
    station_code: str | None
    station_name: str | None
    latitude: float | None
    longitude: float | None
    country_code: str | None
    observed_at: str | None
    variable_code: str | None
    value: float | None
    unit: str | None
    sensor_code: str | None = None
    qc_flag: str = "unchecked"
    qc_notes: str | None = None


class BaseTextPayloadParser(ABC):
    format_name: str = "base"

    @abstractmethod
    def matches(self, text: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, text: str) -> list[ExtractedStationObservation]:
        raise NotImplementedError


@ParserRegistry.register_text_parser
class SimpleKeyValueTextParser(BaseTextPayloadParser):
    format_name = "simple_key_value"

    def matches(self, text: str) -> bool:
        return "OBSERVED_AT=" in text and "VARIABLE=" in text and "VALUE=" in text

    def _to_float(self, value: str | None) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except Exception:
            return None

    def parse(self, text: str) -> list[ExtractedStationObservation]:
        rows: list[ExtractedStationObservation] = []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            parts: dict[str, str] = {}
            for item in line.split(","):
                if "=" not in item:
                    continue
                key, value = item.split("=", 1)
                parts[key.strip().upper()] = value.strip()

            rows.append(
                ExtractedStationObservation(
                    source_name=parts.get("SOURCE_NAME"),
                    wmo_id=parts.get("WMO_ID"),
                    station_code=parts.get("STATION_CODE"),
                    station_name=parts.get("STATION_NAME"),
                    latitude=self._to_float(parts.get("LAT")),
                    longitude=self._to_float(parts.get("LON")),
                    country_code=parts.get("COUNTRY_CODE"),
                    observed_at=parts.get("OBSERVED_AT"),
                    variable_code=parts.get("VARIABLE"),
                    value=self._to_float(parts.get("VALUE")),
                    unit=parts.get("UNIT"),
                    sensor_code=parts.get("SENSOR_CODE"),
                    qc_flag=parts.get("QC_FLAG", "unchecked"),
                    qc_notes=parts.get("QC_NOTES"),
                )
            )

        return rows


class BaseMETARParser(BaseTextPayloadParser):
    report_type: str = "METAR"

    metar_re = re.compile(
        r"^(?:METAR|SPECI)\s+"
        r"(?P<icao>[A-Z]{4})\s+"
        r"(?P<day>\d{2})(?P<hour>\d{2})(?P<minute>\d{2})Z\s+"
        r"(?P<wind_dir>\d{3}|VRB)(?P<wind_speed>\d{2,3})KT\s+"
        r"(?P<visibility>\d{4}|9999).*?"
        r"(?P<temp>M?\d{2})/(?P<dew>M?\d{2})\s+"
        r"Q(?P<pressure>\d{4})",
        re.IGNORECASE,
    )

    def _parse_signed_temp(self, value: str) -> float:
        return -float(value[1:]) if value.startswith("M") else float(value)

    def _iso_from_ddhhmm(self, day: str, hour: str, minute: str) -> str | None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        try:
            return datetime(
                year=now.year,
                month=now.month,
                day=int(day),
                hour=int(hour),
                minute=int(minute),
                tzinfo=timezone.utc,
            ).isoformat()
        except Exception:
            return None

    def _build_rows(self, text: str) -> list[ExtractedStationObservation]:
        text = text.strip()
        match = self.metar_re.search(text)
        if not match:
            return []

        icao = match.group("icao").upper()
        observed_at = self._iso_from_ddhhmm(
            match.group("day"),
            match.group("hour"),
            match.group("minute"),
        )
        wind_dir_raw = match.group("wind_dir")
        wind_speed = float(match.group("wind_speed"))
        visibility = None if match.group("visibility") == "9999" else float(match.group("visibility"))
        temp = self._parse_signed_temp(match.group("temp"))
        dew = self._parse_signed_temp(match.group("dew"))
        pressure = float(match.group("pressure"))
        wind_dir = None if wind_dir_raw == "VRB" else float(wind_dir_raw)

        rows = [
            ExtractedStationObservation(
                source_name=self.report_type.lower(),
                wmo_id=None,
                station_code=icao,
                station_name=None,
                latitude=None,
                longitude=None,
                country_code=None,
                observed_at=observed_at,
                variable_code="temp",
                value=temp,
                unit="degC",
                sensor_code="TEMP_AUTO",
            ),
            ExtractedStationObservation(
                source_name=self.report_type.lower(),
                wmo_id=None,
                station_code=icao,
                station_name=None,
                latitude=None,
                longitude=None,
                country_code=None,
                observed_at=observed_at,
                variable_code="dewpoint",
                value=dew,
                unit="degC",
                sensor_code="DEW_AUTO",
            ),
            ExtractedStationObservation(
                source_name=self.report_type.lower(),
                wmo_id=None,
                station_code=icao,
                station_name=None,
                latitude=None,
                longitude=None,
                country_code=None,
                observed_at=observed_at,
                variable_code="wind_speed",
                value=wind_speed,
                unit="kt",
                sensor_code="WINDSPD_AUTO",
            ),
            ExtractedStationObservation(
                source_name=self.report_type.lower(),
                wmo_id=None,
                station_code=icao,
                station_name=None,
                latitude=None,
                longitude=None,
                country_code=None,
                observed_at=observed_at,
                variable_code="pressure",
                value=pressure,
                unit="hPa",
                sensor_code="PRESS_AUTO",
            ),
        ]

        if wind_dir is not None:
            rows.append(
                ExtractedStationObservation(
                    source_name=self.report_type.lower(),
                    wmo_id=None,
                    station_code=icao,
                    station_name=None,
                    latitude=None,
                    longitude=None,
                    country_code=None,
                    observed_at=observed_at,
                    variable_code="wind_direction",
                    value=wind_dir,
                    unit="deg",
                    sensor_code="WINDDIR_AUTO",
                )
            )

        if visibility is not None:
            rows.append(
                ExtractedStationObservation(
                    source_name=self.report_type.lower(),
                    wmo_id=None,
                    station_code=icao,
                    station_name=None,
                    latitude=None,
                    longitude=None,
                    country_code=None,
                    observed_at=observed_at,
                    variable_code="visibility",
                    value=visibility,
                    unit="m",
                    sensor_code="VIS_AUTO",
                )
            )

        return rows


@ParserRegistry.register_text_parser
class METARTextParser(BaseMETARParser):
    format_name = "metar"
    report_type = "METAR"

    def matches(self, text: str) -> bool:
        first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
        return first_line.startswith("METAR ")

    def parse(self, text: str) -> list[ExtractedStationObservation]:
        return self._build_rows(text)


@ParserRegistry.register_text_parser
class SPECITextParser(BaseMETARParser):
    format_name = "speci"
    report_type = "SPECI"

    def matches(self, text: str) -> bool:
        first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
        return first_line.startswith("SPECI ")

    def parse(self, text: str) -> list[ExtractedStationObservation]:
        return self._build_rows(text)


@ParserRegistry.register_text_parser
class SYNOPAAXXParser(BaseTextPayloadParser):
    """Parse WMO SYNOP AAXX land-surface synoptic messages."""

    format_name = "synop_aaxx"

    _HEADER_RE = re.compile(r"AAXX\s+(\d{2})(\d{2})(\d)")
    _SECTION_MARKERS = {"333", "444", "555"}

    def matches(self, text: str) -> bool:
        return "AAXX " in text

    def parse(self, text: str) -> list[ExtractedStationObservation]:
        text = text.replace("\r", "\n")
        m = self._HEADER_RE.search(text)
        if not m:
            return []

        day, hour, wind_ind = m.group(1), m.group(2), m.group(3)
        observed_at = self._obs_time(int(day), int(hour))
        speed_unit = "kt" if wind_ind in ("3", "4") else "m/s"

        rows: list[ExtractedStationObservation] = []
        for block in text[m.end():].split("="):
            rows.extend(self._parse_block(block, observed_at, speed_unit))
        return rows

    def _parse_block(
        self, block: str, observed_at: str | None, speed_unit: str
    ) -> list[ExtractedStationObservation]:
        tokens = block.split()
        if not tokens:
            return []

        # Find 5-digit WMO station number (skip NIL/section markers before it)
        i = 0
        while i < len(tokens) and tokens[i] in self._SECTION_MARKERS | {"NIL"}:
            i += 1
        if i >= len(tokens) or not re.fullmatch(r"\d{5}", tokens[i]):
            return []

        wmo_id = tokens[i]
        # groups[0]=iRiXhVV, groups[1]=Nddff, groups[2:]=observation data
        groups = tokens[i + 1:]
        sec_break = next(
            (j for j, g in enumerate(groups) if g in self._SECTION_MARKERS),
            len(groups),
        )
        main_groups = groups[:sec_break]

        rows: list[ExtractedStationObservation] = []

        def row(var: str, val: float, unit: str) -> ExtractedStationObservation:
            return ExtractedStationObservation(
                source_name="synop_aaxx",
                wmo_id=wmo_id,
                station_code=wmo_id,
                station_name=None,
                latitude=None,
                longitude=None,
                country_code=None,
                observed_at=observed_at,
                variable_code=var,
                value=val,
                unit=unit,
            )

        for idx, g in enumerate(main_groups):
            if len(g) != 5 or g == "/////":
                continue
            if idx == 0:  # iRiXhVV — precipitation/weather indicators, skip
                continue
            if idx == 1:  # Nddff — wind
                dd, ff = g[1:3], g[3:5]
                if "/" not in dd and "/" not in ff:
                    direction = int(dd) * 10
                    speed = int(ff)
                    if direction <= 360:
                        rows.append(row("wind_direction", float(direction), "deg"))
                    if speed > 0:
                        rows.append(row("wind_speed", float(speed), speed_unit))
                continue

            p = g[0]
            if p == "1":    # 1sTTT — air temperature
                val = self._signed_temp(g[1], g[2:])
                if val is not None:
                    rows.append(row("temp", val, "degC"))
            elif p == "2":  # 2sTTT — dewpoint
                val = self._signed_temp(g[1], g[2:])
                if val is not None:
                    rows.append(row("dewpoint", val, "degC"))
            elif p == "3":  # 3PPPP — station pressure
                val = self._decode_pressure(g[1:])
                if val is not None:
                    rows.append(row("station_pressure", val, "hPa"))
            elif p == "4":  # 4PPPP — MSL pressure
                val = self._decode_pressure(g[1:])
                if val is not None:
                    rows.append(row("msl_pressure", val, "hPa"))

        return rows

    @staticmethod
    def _signed_temp(sign: str, digits: str) -> float | None:
        if "/" in sign + digits:
            return None
        return (-1.0 if sign == "1" else 1.0) * int(digits) / 10

    @staticmethod
    def _decode_pressure(pppp: str) -> float | None:
        """Decode 4-digit pressure group: values ≥5000 are 500–999.9 hPa; <5000 are 1000–1499.9 hPa."""
        if "/" in pppp:
            return None
        v = int(pppp)
        return (v / 10) if v >= 5000 else (v / 10 + 1000)

    @staticmethod
    def _obs_time(day: int, hour: int) -> str | None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        try:
            return datetime(now.year, now.month, day, hour, 0, tzinfo=timezone.utc).isoformat()
        except Exception:
            return None


class NullTextPayloadParser(BaseTextPayloadParser):
    format_name = "null"

    def matches(self, text: str) -> bool:
        return True

    def parse(self, text: str) -> list[ExtractedStationObservation]:
        return []


class TextPayloadParserFactory:
    @classmethod
    def get_parser(cls, text: str) -> BaseTextPayloadParser:
        for parser_cls in ParserRegistry.get_text_parsers():
            parser = parser_cls()
            if parser.matches(text):
                return parser
        return NullTextPayloadParser()
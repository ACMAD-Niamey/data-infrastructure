"""Static configuration for the heat-campaign CSV format."""

from __future__ import annotations

from dataclasses import dataclass

# Loggers record GPS fixes at boot, so a unit that was bench-tested elsewhere
# (e.g. sensor 006 started in Belgium) still carries foreign fixes. Only fixes
# inside this box count as "deployed"; everything before the first one is
# pre-deployment data and is skipped.
NIAMEY_BBOX = (13.30, 1.90, 13.70, 2.30)  # (min_lat, min_lon, max_lat, max_lon)

DEFAULT_COUNTRY_CODE = "NER"
DEFAULT_COUNTRY_NAME = "Niger"

GPS_PHASE_PREFIX = "GPS"
MEASUREMENT_PHASE = "MIN1"


@dataclass(frozen=True)
class VariableSpec:
    """Maps one CSV column to an observation variable."""

    column: str
    variable_code: str
    unit: str


# The CSV column doubles as the StationSensor.sensor_code, so a sensor row is
# traceable back to the logger channel it came from.
VARIABLES: tuple[VariableSpec, ...] = (
    VariableSpec("dht_temp_c", "temp", "degC"),
    VariableSpec("dht_rh_pct", "rh", "%"),
    VariableSpec("ds18b20_temp_c", "globe_temp", "degC"),
    VariableSpec("lux", "lux", "lx"),
    VariableSpec("batt_v", "battery_v", "V"),
)

# French labels used in the field folder/file names -> normalised exposure.
EXPOSURE_BY_LABEL = {"soleil": "sun", "ombre": "shade"}
EXPOSURE_LABEL_EN = {"sun": "Sun", "shade": "Shade"}

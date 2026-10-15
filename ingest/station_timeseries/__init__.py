"""Ingestion of station time-series datasets (low-cost sensor CSV loggers).

Pipeline: filename -> parser -> geocoder (place name) -> registry (Station /
StationSensor) -> service (observations). Each step lives in its own module so
a new logger format only needs a new parser.
"""

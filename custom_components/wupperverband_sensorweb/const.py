"""Constants for Wupperverband Sensor Web."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "wupperverband_sensorweb"
DEFAULT_ENDPOINT = "https://fluggs.wupperverband.de/sws5/service"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=10)
DEFAULT_UPDATE_INTERVAL_MINUTES = 10
MIN_UPDATE_INTERVAL_MINUTES = 5
MAX_UPDATE_INTERVAL_MINUTES = 1440
MAX_OBSERVATION_AGE = timedelta(hours=24)
METADATA_CACHE_TTL = timedelta(hours=48)
METADATA_CACHE_STORAGE_KEY = f"{DOMAIN}.metadata_cache"
METADATA_CACHE_STORAGE_VERSION = 1

CONF_ENDPOINT = "endpoint"
CONF_OFFERING = "offering"
CONF_OBSERVED_PROPERTY = "observed_property"
CONF_STATION = "station"
CONF_TIMESERIES = "timeseries"
CONF_DISPLAY_NAME = "display_name"
CONF_UPDATE_INTERVAL = "update_interval"

ATTRIBUTION = "Datenquelle: © Wupperverband {year}"
TERMS_URL = (
    "https://fluggs.wupperverband.de/v2p/web/fluggs/"
    "nutzungsbedingungen-digitale-dienste"
)
SOURCE_URL = "https://www.wupperverband.de/service/gis-fluggs-sensor-web"
MANUFACTURER = "Wupperverband"

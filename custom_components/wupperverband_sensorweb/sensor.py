"""Sensor platform for Wupperverband Sensor Web."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTRIBUTION,
    CONF_DISPLAY_NAME,
    CONF_OBSERVED_PROPERTY,
    CONF_OFFERING,
    CONF_STALE_AFTER,
    CONF_STATION,
    CONF_TIMESERIES,
    DEFAULT_STALE_AFTER_MINUTES,
    DOMAIN,
    MANUFACTURER,
    SOURCE_URL,
)
from .coordinator import WupperverbandCoordinator
from .models import Observation

UNIT_MAP = {
    "Cel": UnitOfTemperature.CELSIUS,
    "degC": UnitOfTemperature.CELSIUS,
    "°C": UnitOfTemperature.CELSIUS,
    "%": PERCENTAGE,
    "percent": PERCENTAGE,
    "m": UnitOfLength.METERS,
    "mNN": UnitOfLength.METERS,
    "mNHN": UnitOfLength.METERS,
    "cm": UnitOfLength.CENTIMETERS,
    "mm": UnitOfLength.MILLIMETERS,
    "m3/s": UnitOfVolumeFlowRate.CUBIC_METERS_PER_SECOND,
    "m³/s": UnitOfVolumeFlowRate.CUBIC_METERS_PER_SECOND,
}


def _native_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    return UNIT_MAP.get(unit, unit)


def _as_utc(timestamp: datetime | None) -> datetime | None:
    """Normalize a source timestamp for reliable comparisons."""
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[WupperverbandCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the configured measurement sensor."""
    async_add_entities(
        [
            WupperverbandSensor(entry),
            WupperverbandLastSuccessfulFetchSensor(entry),
        ]
    )


class WupperverbandSensor(CoordinatorEntity[WupperverbandCoordinator], SensorEntity):
    """Representation of the newest selected SOS measurement."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    # Record every successful poll, even when the source value is unchanged.
    # This makes repeated source samples visible in HA history/statistics.
    _attr_force_update = True

    def __init__(self, entry: ConfigEntry[WupperverbandCoordinator]) -> None:
        super().__init__(entry.runtime_data)
        self._entry = entry
        station = entry.data.get(CONF_STATION) or entry.data.get(CONF_OFFERING)
        timeseries = entry.data.get(CONF_TIMESERIES)
        observed_property = entry.data.get(CONF_OBSERVED_PROPERTY)
        self._attr_unique_id = timeseries or f"{station}|{observed_property}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station)},
            name=entry.data.get(CONF_DISPLAY_NAME, entry.title),
            manufacturer=MANUFACTURER,
            model="Sensor Observation Service (SOS 2.0)",
            configuration_url=SOURCE_URL,
        )

    @property
    def native_value(self) -> float | str | None:
        """Return current measurement value."""
        return self.coordinator.data.value if self.coordinator.data else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return service-provided unit."""
        return _native_unit(self.coordinator.data.unit) if self.coordinator.data else None

    @property
    def available(self) -> bool:
        """Remain available while the last successful value is present.

        Source age is reported separately as ``data_stale``. An old source
        timestamp must not erase the last valid numeric state or interrupt
        recorder/statistics. Communication failures continue to be represented
        by the coordinator's availability state.
        """
        return super().available and self.coordinator.data is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose provenance, freshness and original SOS metadata."""
        data: Observation | None = self.coordinator.data
        if data is None:
            return {
                "attribution": ATTRIBUTION.format(year=datetime.now().year),
                "station": self._entry.data.get(CONF_STATION),
                "timeseries": self._entry.data.get(CONF_TIMESERIES),
                "offering": self._entry.data.get(CONF_OFFERING),
                "observed_property": self._entry.data.get(CONF_OBSERVED_PROPERTY),
            }

        now = datetime.now(UTC)
        stale_after = self._entry.options.get(
            CONF_STALE_AFTER, DEFAULT_STALE_AFTER_MINUTES
        )
        measurement_time = _as_utc(data.timestamp)
        measurement_age: float | None = None
        if measurement_time is not None:
            measurement_age = max(
                0.0, (now - measurement_time).total_seconds() / 60
            )

        attrs: dict[str, Any] = {
            "attribution": ATTRIBUTION.format(year=now.year),
            "station": self._entry.data.get(CONF_STATION),
            "timeseries": self._entry.data.get(CONF_TIMESERIES),
            "offering": self._entry.data.get(CONF_OFFERING),
            "observed_property": self._entry.data.get(CONF_OBSERVED_PROPERTY),
            "poll_interval_minutes": (
                int(self.coordinator.update_interval.total_seconds() / 60)
                if self.coordinator.update_interval
                else None
            ),
            "stale_after_minutes": stale_after,
            "data_stale": (
                measurement_age is not None and measurement_age > stale_after
            ),
        }
        if measurement_time is not None:
            attrs["measurement_time"] = measurement_time.isoformat()
            attrs["measurement_age_minutes"] = round(measurement_age or 0.0, 1)
        if data.result_time is not None:
            result_time = _as_utc(data.result_time)
            if result_time is not None:
                attrs["result_time"] = result_time.isoformat()
        if self.coordinator.last_successful_fetch is not None:
            attrs["last_successful_fetch"] = (
                self.coordinator.last_successful_fetch.isoformat()
            )
        if data.procedure:
            attrs["procedure"] = data.procedure
        if data.feature_of_interest:
            attrs["feature_of_interest"] = data.feature_of_interest
        return attrs


class WupperverbandLastSuccessfulFetchSensor(
    CoordinatorEntity[WupperverbandCoordinator], SensorEntity, RestoreEntity
):
    """Diagnostic timestamp of the last successful upstream fetch."""

    _attr_has_entity_name = True
    _attr_name = "Last successful fetch"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry[WupperverbandCoordinator]) -> None:
        super().__init__(entry.runtime_data)
        station = entry.data.get(CONF_STATION) or entry.data.get(CONF_OFFERING)
        timeseries = entry.data.get(CONF_TIMESERIES)
        observed_property = entry.data.get(CONF_OBSERVED_PROPERTY)
        self._attr_unique_id = (
            f"{timeseries}|last_successful_fetch"
            if timeseries is not None
            else f"{station}|{observed_property}|last_successful_fetch"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station)},
            name=entry.data.get(CONF_DISPLAY_NAME, entry.title),
            manufacturer=MANUFACTURER,
            model="Sensor Observation Service (SOS 2.0)",
            configuration_url=SOURCE_URL,
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last successful fetch timestamp across restarts."""
        await super().async_added_to_hass()

        if self.coordinator.last_successful_fetch is not None:
            return

        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        restored = dt_util.parse_datetime(last_state.state)
        if restored is None:
            return

        self.coordinator.last_successful_fetch = _as_utc(restored)
        self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | None:
        """Return when the latest successful poll completed."""
        return self.coordinator.last_successful_fetch

    @property
    def available(self) -> bool:
        """Expose availability once at least one fetch succeeded."""
        return self.coordinator.last_successful_fetch is not None

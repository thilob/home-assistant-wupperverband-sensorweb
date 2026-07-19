"""Sensor platform for Wupperverband Sensor Web."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_DISPLAY_NAME,
    CONF_STATION,
    CONF_TIMESERIES,
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
    "cm": UnitOfLength.CENTIMETERS,
    "mm": UnitOfLength.MILLIMETERS,
    "m3/s": UnitOfVolumeFlowRate.CUBIC_METERS_PER_SECOND,
    "m³/s": UnitOfVolumeFlowRate.CUBIC_METERS_PER_SECOND,
}


def _native_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    return UNIT_MAP.get(unit, unit)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[WupperverbandCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the configured measurement sensor."""
    async_add_entities([WupperverbandSensor(entry)])


class WupperverbandSensor(CoordinatorEntity[WupperverbandCoordinator], SensorEntity):
    """Representation of the newest selected SOS measurement."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry[WupperverbandCoordinator]) -> None:
        super().__init__(entry.runtime_data)
        self._entry = entry
        station = entry.data[CONF_STATION]
        timeseries = entry.data[CONF_TIMESERIES]
        self._attr_unique_id = timeseries
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
        return (
            _native_unit(self.coordinator.data.unit) if self.coordinator.data else None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose provenance and original SOS metadata."""
        data: Observation = self.coordinator.data
        attrs: dict[str, Any] = {
            "attribution": ATTRIBUTION.format(year=datetime.now().year),
            "station": self._entry.data[CONF_STATION],
            "timeseries": self._entry.data[CONF_TIMESERIES],
        }
        if data.timestamp:
            attrs["measurement_time"] = data.timestamp.isoformat()
        if data.procedure:
            attrs["procedure"] = data.procedure
        if data.feature_of_interest:
            attrs["feature_of_interest"] = data.feature_of_interest
        return attrs

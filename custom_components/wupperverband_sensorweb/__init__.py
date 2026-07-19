"""Wupperverband Sensor Web integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WupperverbandSosClient
from .const import (
    CONF_ENDPOINT,
    CONF_TIMESERIES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
)
from .coordinator import WupperverbandCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type WupperverbandConfigEntry = ConfigEntry[WupperverbandCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: WupperverbandConfigEntry
) -> bool:
    """Set up Wupperverband Sensor Web from a config entry."""
    session = async_get_clientsession(hass)
    client = WupperverbandSosClient(session, entry.data[CONF_ENDPOINT])
    minutes = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES)
    coordinator = WupperverbandCoordinator(
        hass,
        client,
        entry.data[CONF_TIMESERIES],
        timedelta(minutes=minutes),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: WupperverbandConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: WupperverbandConfigEntry
) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)

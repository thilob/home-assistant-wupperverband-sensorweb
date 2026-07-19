"""Persistent cache for Wupperverband station metadata."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any, TypeVar

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .api import WupperverbandApiError, WupperverbandSosClient
from .const import (
    DOMAIN,
    METADATA_CACHE_STORAGE_KEY,
    METADATA_CACHE_STORAGE_VERSION,
    METADATA_CACHE_TTL,
)
from .models import Station, TimeSeries

_CACHE_INSTANCE = "metadata_cache"
_T = TypeVar("_T")


class WupperverbandMetadataCache:
    """Cache large, slow-changing metadata lists across HA restarts."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass,
            METADATA_CACHE_STORAGE_VERSION,
            METADATA_CACHE_STORAGE_KEY,
        )
        self._data: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    async def _async_data(self) -> dict[str, Any]:
        if self._data is None:
            self._data = await self._store.async_load() or {
                "stations": {},
                "timeseries": {},
            }
            self._data.setdefault("stations", {})
            self._data.setdefault("timeseries", {})
        return self._data

    @staticmethod
    def _is_fresh(record: dict[str, Any]) -> bool:
        return (
            time.time() - record.get("updated_at", 0)
            < METADATA_CACHE_TTL.total_seconds()
        )

    async def _async_cached_list(
        self,
        section: str,
        key: str,
        fetch: Callable[[], Awaitable[list[_T]]],
        deserialize: Callable[[dict[str, Any]], _T],
    ) -> list[_T]:
        async with self._lock:
            data = await self._async_data()
            record = data[section].get(key)
            if record and self._is_fresh(record):
                return [deserialize(item) for item in record["items"]]

            try:
                items = await fetch()
            except WupperverbandApiError:
                # Station metadata remains useful during a temporary API outage,
                # even after the regular 48-hour freshness window has elapsed.
                if record:
                    return [deserialize(item) for item in record["items"]]
                raise

            data[section][key] = {
                "updated_at": time.time(),
                "items": [asdict(item) for item in items],
            }
            await self._store.async_save(data)
            return items

    async def async_get_stations(self, client: WupperverbandSosClient) -> list[Station]:
        """Return stations, refreshing the persistent cache every 48 hours."""
        return await self._async_cached_list(
            "stations",
            client.api_endpoint,
            client.async_get_stations,
            lambda item: Station(**item),
        )

    async def async_get_timeseries(
        self, client: WupperverbandSosClient, station_id: str
    ) -> list[TimeSeries]:
        """Return a station's series definitions from the metadata cache."""
        return await self._async_cached_list(
            "timeseries",
            f"{client.api_endpoint}|{station_id}",
            lambda: client.async_get_timeseries(station_id),
            lambda item: TimeSeries(**item),
        )


def async_get_metadata_cache(hass: HomeAssistant) -> WupperverbandMetadataCache:
    """Return the single cache instance shared by all config flows."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if _CACHE_INSTANCE not in domain_data:
        domain_data[_CACHE_INSTANCE] = WupperverbandMetadataCache(hass)
    return domain_data[_CACHE_INSTANCE]

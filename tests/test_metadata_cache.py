import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from conftest import FakeStore

from custom_components.wupperverband_sensorweb import metadata_cache as cache_module
from custom_components.wupperverband_sensorweb.api import WupperverbandConnectionError
from custom_components.wupperverband_sensorweb.metadata_cache import (
    WupperverbandMetadataCache,
)
from custom_components.wupperverband_sensorweb.models import Station, TimeSeries


@pytest.fixture(autouse=True)
def clear_store() -> None:
    FakeStore.saved.clear()


def test_station_metadata_is_cached_for_48_hours() -> None:
    station = Station("47", "Unterburg-Wupper", 7.14, 51.13)
    client = SimpleNamespace(
        api_endpoint="https://example.test/api/",
        async_get_stations=AsyncMock(return_value=[station]),
    )
    cache = WupperverbandMetadataCache(SimpleNamespace())

    first = asyncio.run(cache.async_get_stations(client))
    second = asyncio.run(cache.async_get_stations(client))

    assert first == second == [station]
    client.async_get_stations.assert_awaited_once()


def test_expired_metadata_is_refreshed(monkeypatch) -> None:
    old_station = Station("47", "Alter Name")
    new_station = Station("47", "Unterburg-Wupper")
    client = SimpleNamespace(
        api_endpoint="https://example.test/api/",
        async_get_stations=AsyncMock(side_effect=[[old_station], [new_station]]),
    )
    cache = WupperverbandMetadataCache(SimpleNamespace())

    monkeypatch.setattr(cache_module.time, "time", lambda: 1_000_000)
    assert asyncio.run(cache.async_get_stations(client)) == [old_station]
    monkeypatch.setattr(cache_module.time, "time", lambda: 1_172_801)
    assert asyncio.run(cache.async_get_stations(client)) == [new_station]
    assert client.async_get_stations.await_count == 2


def test_stale_metadata_is_fallback_during_outage(monkeypatch) -> None:
    station = Station("47", "Unterburg-Wupper")
    client = SimpleNamespace(
        api_endpoint="https://example.test/api/",
        async_get_stations=AsyncMock(
            side_effect=[[station], WupperverbandConnectionError("temporary outage")]
        ),
    )
    cache = WupperverbandMetadataCache(SimpleNamespace())

    monkeypatch.setattr(cache_module.time, "time", lambda: 1_000_000)
    asyncio.run(cache.async_get_stations(client))
    monkeypatch.setattr(cache_module.time, "time", lambda: 1_172_801)

    assert asyncio.run(cache.async_get_stations(client)) == [station]


def test_timeseries_definitions_are_cached_per_station() -> None:
    series = TimeSeries("24", "Abfluss", "47", "Unterburg", "Abfluss")
    client = SimpleNamespace(
        api_endpoint="https://example.test/api/",
        async_get_timeseries=AsyncMock(return_value=[series]),
    )
    cache = WupperverbandMetadataCache(SimpleNamespace())

    first = asyncio.run(cache.async_get_timeseries(client, "47"))
    second = asyncio.run(cache.async_get_timeseries(client, "47"))

    assert first == second == [series]
    client.async_get_timeseries.assert_awaited_once_with("47")

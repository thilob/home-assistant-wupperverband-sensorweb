import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from custom_components.wupperverband_sensorweb.api import (
    WupperverbandInvalidResponseError,
    WupperverbandSosClient,
    humanize_identifier,
    parse_capabilities,
    parse_observation,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_capabilities() -> None:
    offerings = parse_capabilities((FIXTURES / "capabilities.xml").read_bytes())
    assert len(offerings) == 1
    assert offerings[0].identifier == "offering-1"
    assert offerings[0].name == "Pegel Beispiel"
    assert offerings[0].observed_properties == (
        "urn:property:water-level",
        "urn:property:discharge",
    )
    assert offerings[0].features_of_interest == ("urn:feature:station-1",)


def test_parse_observation() -> None:
    observation = parse_observation((FIXTURES / "observation.xml").read_bytes())
    assert observation.value == 123.4
    assert observation.unit == "cm"
    assert observation.timestamp is not None
    assert observation.timestamp.isoformat() == "2026-07-19T17:00:00+00:00"
    assert observation.observed_property == "urn:property:water-level"


def test_exception_response_is_reported() -> None:
    xml = b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"><ows:Exception><ows:ExceptionText>bad request</ows:ExceptionText></ows:Exception></ows:ExceptionReport>'
    with pytest.raises(WupperverbandInvalidResponseError, match="bad request"):
        parse_observation(xml)


def test_humanize_identifier() -> None:
    assert (
        humanize_identifier("https://example.test/observed/water-level")
        == "water level"
    )


def test_api_endpoint_is_derived_from_sos_endpoint() -> None:
    client = WupperverbandSosClient(None, "https://example.test/sws5/service")
    assert client.api_endpoint == "https://example.test/sws5/api/"


def test_station_and_timeseries_selection() -> None:
    client = WupperverbandSosClient(None, "https://example.test/sws5/service")
    client._get_json = AsyncMock(
        side_effect=[
            [
                {
                    "id": "47",
                    "properties": {"label": "Unterburg-Wupper"},
                    "geometry": {"coordinates": [7.14, 51.13]},
                }
            ],
            [
                {
                    "id": "24",
                    "label": "Abfluss, Einzelwerte, Unterburg-Wupper",
                    "uom": "m³/s",
                    "feature": {
                        "id": "47",
                        "properties": {"label": "Unterburg-Wupper"},
                    },
                    "parameters": {
                        "phenomenon": {"label": "Abfluss"},
                        "procedure": {"label": "Einzelwerte"},
                    },
                },
                {"id": "wrong-station", "feature": {"id": "99"}},
            ],
        ]
    )

    stations = asyncio.run(client.async_get_stations())
    series = asyncio.run(client.async_get_timeseries("47"))

    assert stations[0].name == "Unterburg-Wupper"
    assert stations[0].latitude == 51.13
    assert len(series) == 1
    assert series[0].identifier == "24"
    assert series[0].phenomenon == "Abfluss"

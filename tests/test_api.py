import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, call

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


def _client_with_responses(
    *payloads: bytes,
) -> tuple[WupperverbandSosClient, SimpleNamespace]:
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        read=AsyncMock(side_effect=payloads),
    )
    session = SimpleNamespace(get=AsyncMock(return_value=response))
    return WupperverbandSosClient(
        session, "https://example.test/sws5/service"
    ), session


def test_sos_requests_use_expected_parameters() -> None:
    client, session = _client_with_responses(
        (FIXTURES / "capabilities.xml").read_bytes(),
        (FIXTURES / "observation.xml").read_bytes(),
    )

    offerings = asyncio.run(client.async_get_offerings())
    observation = asyncio.run(
        client.async_get_latest_observation(
            "offering-1", "urn:property:water-level"
        )
    )

    assert offerings[0].identifier == "offering-1"
    assert observation.value == 123.4
    assert session.get.await_args_list[0].kwargs["params"] == {
        "service": "SOS",
        "version": "2.0.0",
        "request": "GetCapabilities",
    }
    assert session.get.await_args_list[1].kwargs["params"] == {
        "service": "SOS",
        "version": "2.0.0",
        "request": "GetObservation",
        "offering": "offering-1",
        "observedProperty": "urn:property:water-level",
        "temporalFilter": "om:phenomenonTime,latest",
        "responseFormat": "http://www.opengis.net/om/2.0",
    }


def test_measurement_requests_are_not_cached() -> None:
    payload = (FIXTURES / "observation.xml").read_bytes()
    client, session = _client_with_responses(payload, payload)

    asyncio.run(client.async_get_latest_observation("offering-1", "property-1"))
    asyncio.run(client.async_get_latest_observation("offering-1", "property-1"))

    expected_headers = {
        "Cache-Control": "no-cache, no-store, max-age=0",
        "Pragma": "no-cache",
    }
    assert session.get.await_count == 2
    assert session.get.await_args_list == [
        call(
            "https://example.test/sws5/service",
            params=session.get.await_args_list[0].kwargs["params"],
            headers=expected_headers,
        ),
        call(
            "https://example.test/sws5/service",
            params=session.get.await_args_list[1].kwargs["params"],
            headers=expected_headers,
        ),
    ]


def test_observation_without_result_is_rejected() -> None:
    with pytest.raises(WupperverbandInvalidResponseError, match="No observation"):
        parse_observation(
            b'<om:OM_Observation xmlns:om="http://www.opengis.net/om/2.0" />'
        )


def test_invalid_observation_xml_is_rejected() -> None:
    with pytest.raises(
        WupperverbandInvalidResponseError, match="Invalid observation XML"
    ):
        parse_observation(b"<not-closed>")

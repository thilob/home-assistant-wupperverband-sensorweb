from pathlib import Path

import pytest

from custom_components.wupperverband_sensorweb.api import (
    WupperverbandInvalidResponseError,
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
    assert humanize_identifier("https://example.test/observed/water-level") == "water level"


def test_parse_observation_selects_newest_with_mixed_timezone_input() -> None:
    observation = parse_observation(
        (FIXTURES / "observation_multiple.xml").read_bytes()
    )
    assert observation.value == 300.2
    assert observation.timestamp is not None
    assert observation.timestamp.isoformat() == "2026-07-21T09:00:00+00:00"
    assert observation.result_time is not None
    assert observation.result_time.isoformat() == "2026-07-21T09:01:00+00:00"

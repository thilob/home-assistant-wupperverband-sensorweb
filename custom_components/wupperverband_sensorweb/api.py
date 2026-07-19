"""Asynchronous OGC SOS 2.0 client for Wupperverband Sensor Web."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from datetime import datetime
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

from aiohttp import ClientError, ClientResponseError, ClientSession

from .models import Observation, Offering, Station, TimeSeries

_LOGGER = logging.getLogger(__name__)

SOS_VERSION = "2.0.0"
REQUEST_TIMEOUT_SECONDS = 30


class WupperverbandApiError(Exception):
    """Base API error."""


class WupperverbandConnectionError(WupperverbandApiError):
    """Connection to the SOS failed."""


class WupperverbandInvalidResponseError(WupperverbandApiError):
    """The SOS response could not be interpreted."""


def humanize_identifier(identifier: str) -> str:
    """Create a readable fallback label from a URI or identifier."""
    value = unquote(identifier.rstrip("/"))
    parsed = urlparse(value)
    candidate = parsed.fragment or parsed.path.rsplit("/", 1)[-1] or value
    candidate = candidate.replace("_", " ").replace("-", " ").strip()
    return candidate or identifier


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr_by_local_name(element: ET.Element, name: str) -> str | None:
    for key, value in element.attrib.items():
        if _local_name(key) == name:
            return value
    return None


def _first_text(element: ET.Element, local_names: Iterable[str]) -> str | None:
    wanted = set(local_names)
    for child in element.iter():
        if _local_name(child.tag) in wanted and child.text and child.text.strip():
            return child.text.strip()
    return None


def _references(element: ET.Element, local_name: str) -> tuple[str, ...]:
    values: list[str] = []
    for child in element.iter():
        if _local_name(child.tag) != local_name:
            continue
        value = _attr_by_local_name(child, "href") or (
            child.text.strip() if child.text and child.text.strip() else None
        )
        if value and value not in values:
            values.append(value)
    return tuple(values)


def parse_capabilities(xml_data: bytes | str) -> list[Offering]:
    """Parse SOS 2.0 capabilities into offerings.

    The parser intentionally uses XML local names. This makes it tolerant of
    namespace-prefix differences used by different 52°North SOS versions.
    """
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as err:
        raise WupperverbandInvalidResponseError("Invalid capabilities XML") from err

    exception_text = _first_text(root, ("ExceptionText",))
    if exception_text:
        raise WupperverbandInvalidResponseError(exception_text)

    offerings: list[Offering] = []
    for element in root.iter():
        if _local_name(element.tag) not in {
            "ObservationOffering",
            "observationOffering",
        }:
            continue

        identifier = _first_text(element, ("identifier",))
        if not identifier:
            identifier = _attr_by_local_name(element, "id")
        if not identifier:
            continue

        name = _first_text(element, ("name", "title")) or humanize_identifier(
            identifier
        )
        observed_properties = _references(element, "observableProperty")
        if not observed_properties:
            observed_properties = _references(element, "observedProperty")

        offerings.append(
            Offering(
                identifier=identifier,
                name=name,
                observed_properties=observed_properties,
                procedures=_references(element, "procedure"),
                features_of_interest=_references(element, "featureOfInterest"),
            )
        )

    # Some SOS documents wrap the actual offering in a member and put the
    # identifier on that member. Try a conservative fallback for such variants.
    if not offerings:
        for member in root.iter():
            if _local_name(member.tag) != "observationOffering":
                continue
            identifier = _attr_by_local_name(member, "href")
            if identifier:
                offerings.append(Offering(identifier, humanize_identifier(identifier)))

    if not offerings:
        raise WupperverbandInvalidResponseError("No observation offerings found")

    # Namespace wrappers can expose the same offering twice through recursive
    # lookup. Keep the richest representation for each stable identifier.
    deduplicated: dict[str, Offering] = {}
    for offering in offerings:
        current = deduplicated.get(offering.identifier)
        if current is None or len(offering.observed_properties) > len(
            current.observed_properties
        ):
            deduplicated[offering.identifier] = offering

    return sorted(
        deduplicated.values(), key=lambda item: (item.name.casefold(), item.identifier)
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _coerce_value(value: str) -> float | str:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return value


def parse_observation(xml_data: bytes | str) -> Observation:
    """Parse the newest OM observation contained in a SOS response."""
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as err:
        raise WupperverbandInvalidResponseError("Invalid observation XML") from err

    exception_text = _first_text(root, ("ExceptionText",))
    if exception_text:
        raise WupperverbandInvalidResponseError(exception_text)

    candidates: list[Observation] = []
    measurement_nodes = [
        element
        for element in root.iter()
        if _local_name(element.tag)
        in {"OM_Measurement", "Measurement", "OM_Observation"}
    ]
    if not measurement_nodes:
        measurement_nodes = [root]

    for node in measurement_nodes:
        result_element = next(
            (child for child in node.iter() if _local_name(child.tag) == "result"),
            None,
        )
        if result_element is None:
            continue

        raw_value = (result_element.text or "").strip()
        if not raw_value:
            raw_value = _first_text(result_element, ("value", "Quantity")) or ""
        if not raw_value:
            continue

        unit = _attr_by_local_name(result_element, "uom")
        if not unit:
            uom_element = next(
                (
                    child
                    for child in result_element.iter()
                    if _local_name(child.tag) == "uom"
                ),
                None,
            )
            if uom_element is not None:
                unit = _attr_by_local_name(uom_element, "code") or (
                    uom_element.text.strip() if uom_element.text else None
                )

        time_text = _first_text(node, ("timePosition", "beginPosition", "resultTime"))
        procedure_element = next(
            (child for child in node.iter() if _local_name(child.tag) == "procedure"),
            None,
        )
        feature_element = next(
            (
                child
                for child in node.iter()
                if _local_name(child.tag) == "featureOfInterest"
            ),
            None,
        )
        property_element = next(
            (
                child
                for child in node.iter()
                if _local_name(child.tag) == "observedProperty"
            ),
            None,
        )

        candidates.append(
            Observation(
                value=_coerce_value(raw_value),
                unit=unit,
                timestamp=_parse_datetime(time_text),
                procedure=_attr_by_local_name(procedure_element, "href")
                if procedure_element is not None
                else None,
                feature_of_interest=_attr_by_local_name(feature_element, "href")
                if feature_element is not None
                else None,
                observed_property=_attr_by_local_name(property_element, "href")
                if property_element is not None
                else None,
            )
        )

    if not candidates:
        raise WupperverbandInvalidResponseError("No observation result found")

    return max(candidates, key=lambda item: item.timestamp or datetime.min)


class WupperverbandSosClient:
    """Small async client for the public Wupperverband SOS 2.0 endpoint."""

    def __init__(self, session: ClientSession, endpoint: str) -> None:
        self._session = session
        self.endpoint = endpoint.rstrip("?")

    @property
    def api_endpoint(self) -> str:
        """Return the Sensor Web REST API matching the configured SOS URL."""
        endpoint = self.endpoint.rstrip("/")
        if endpoint.endswith("/service"):
            endpoint = endpoint[: -len("/service")]
        if not endpoint.endswith("/api"):
            endpoint = f"{endpoint}/api"
        return f"{endpoint}/"

    async def _get(self, params: dict[str, str]) -> bytes:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await self._session.get(self.endpoint, params=params)
                response.raise_for_status()
                return await response.read()
        except (TimeoutError, ClientError, ClientResponseError) as err:
            raise WupperverbandConnectionError(str(err)) from err

    async def _get_json(
        self, path: str, params: dict[str, str] | None = None
    ) -> object:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await self._session.get(
                    f"{self.api_endpoint}{path}", params=params
                )
                response.raise_for_status()
                return await response.json(content_type=None)
        except (TimeoutError, ClientError, ClientResponseError) as err:
            raise WupperverbandConnectionError(str(err)) from err
        except (ValueError, TypeError) as err:
            raise WupperverbandInvalidResponseError(
                "Invalid Sensor Web API response"
            ) from err

    async def async_get_stations(self) -> list[Station]:
        """Return monitoring stations exposed by the Sensor Web API."""
        payload = await self._get_json("features", {"locale": "de"})
        if not isinstance(payload, list):
            raise WupperverbandInvalidResponseError("Invalid station list")

        stations: list[Station] = []
        for item in payload:
            if not isinstance(item, dict) or "id" not in item:
                continue
            properties = item.get("properties") or {}
            geometry = item.get("geometry") or {}
            coordinates = geometry.get("coordinates") or []
            stations.append(
                Station(
                    identifier=str(item["id"]),
                    name=str(properties.get("label") or item["id"]),
                    longitude=coordinates[0] if len(coordinates) >= 2 else None,
                    latitude=coordinates[1] if len(coordinates) >= 2 else None,
                )
            )
        if not stations:
            raise WupperverbandInvalidResponseError("No stations found")
        return sorted(stations, key=lambda item: item.name.casefold())

    async def async_get_timeseries(self, station_id: str) -> list[TimeSeries]:
        """Return measurement series available for one station."""
        payload = await self._get_json(
            "timeseries",
            {"features": station_id, "expanded": "true", "locale": "de"},
        )
        if not isinstance(payload, list):
            raise WupperverbandInvalidResponseError("Invalid time series list")

        series: list[TimeSeries] = []
        for item in payload:
            if not isinstance(item, dict) or "id" not in item:
                continue
            feature = item.get("feature") or {}
            properties = feature.get("properties") or {}
            parameters = item.get("parameters") or {}
            phenomenon = parameters.get("phenomenon") or {}
            procedure = parameters.get("procedure") or {}
            item_station_id = str(feature.get("id") or station_id)
            if item_station_id != station_id:
                continue
            series.append(
                TimeSeries(
                    identifier=str(item["id"]),
                    name=str(item.get("label") or item["id"]),
                    station_id=item_station_id,
                    station_name=str(properties.get("label") or station_id),
                    phenomenon=str(
                        phenomenon.get("label")
                        or phenomenon.get("domainId")
                        or item.get("label")
                        or item["id"]
                    ),
                    procedure=(
                        str(procedure.get("label") or procedure.get("domainId"))
                        if procedure
                        else None
                    ),
                    unit=item.get("uom"),
                )
            )
        return sorted(
            series,
            key=lambda item: (
                item.phenomenon.casefold(),
                (item.procedure or "").casefold(),
            ),
        )

    async def async_get_timeseries_observation(self, timeseries_id: str) -> Observation:
        """Return the latest value for one exact measurement series."""
        payload = await self._get_json(f"timeseries/{timeseries_id}", {"locale": "de"})
        if not isinstance(payload, dict):
            raise WupperverbandInvalidResponseError("Invalid time series response")
        latest = payload.get("lastValue") or {}
        if "value" not in latest:
            raise WupperverbandInvalidResponseError("No latest value found")
        feature = payload.get("feature") or {}
        parameters = payload.get("parameters") or {}
        phenomenon = parameters.get("phenomenon") or {}
        procedure = parameters.get("procedure") or {}
        return Observation(
            value=_coerce_value(str(latest["value"])),
            unit=payload.get("uom"),
            timestamp=_parse_datetime(latest.get("timestamp")),
            procedure=str(procedure.get("label") or procedure.get("domainId") or "")
            or None,
            feature_of_interest=str(feature.get("id") or "") or None,
            observed_property=str(
                phenomenon.get("label") or phenomenon.get("domainId") or ""
            )
            or None,
        )

    async def async_get_offerings(self) -> list[Offering]:
        """Return available SOS observation offerings."""
        data = await self._get(
            {
                "service": "SOS",
                "version": SOS_VERSION,
                "request": "GetCapabilities",
            }
        )
        return parse_capabilities(data)

    async def async_get_latest_observation(
        self, offering: str, observed_property: str
    ) -> Observation:
        """Return the latest observation for one offering/property pair."""
        data = await self._get(
            {
                "service": "SOS",
                "version": SOS_VERSION,
                "request": "GetObservation",
                "offering": offering,
                "observedProperty": observed_property,
                # 52°North SOS extension commonly supported by SOS 2.0 servers.
                "temporalFilter": "om:phenomenonTime,latest",
                "responseFormat": "http://www.opengis.net/om/2.0",
            }
        )
        return parse_observation(data)

    async def async_validate(self) -> None:
        """Validate connectivity and basic SOS compatibility."""
        await self.async_get_offerings()

"""Data models for the Wupperverband SOS client."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Station:
    """Station metadata used during config-flow selection."""

    identifier: str
    name: str
    longitude: float | None = None
    latitude: float | None = None


@dataclass(frozen=True, slots=True)
class TimeSeries:
    """A measurement series belonging to one station."""

    identifier: str
    name: str
    station_id: str
    station_name: str
    phenomenon: str
    procedure: str | None = None
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class Offering:
    """An SOS observation offering."""

    identifier: str
    name: str
    observed_properties: tuple[str, ...] = field(default_factory=tuple)
    procedures: tuple[str, ...] = field(default_factory=tuple)
    features_of_interest: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Observation:
    """A single latest observation."""

    value: float | str
    unit: str | None
    timestamp: datetime | None
    result_time: datetime | None = None
    procedure: str | None = None
    feature_of_interest: str | None = None
    observed_property: str | None = None

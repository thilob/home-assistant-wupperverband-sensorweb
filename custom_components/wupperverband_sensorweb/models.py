"""Data models for the Wupperverband SOS client."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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

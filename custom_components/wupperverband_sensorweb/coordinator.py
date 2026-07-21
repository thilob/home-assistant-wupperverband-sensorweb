"""Coordinator for Wupperverband Sensor Web."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WupperverbandApiError, WupperverbandSosClient
from .const import DOMAIN
from .models import Observation

_LOGGER = logging.getLogger(__name__)


class WupperverbandCoordinator(DataUpdateCoordinator[Observation]):
    """Fetch the selected latest observation at a moderate interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: WupperverbandSosClient,
        offering: str,
        observed_property: str,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self.offering = offering
        self.observed_property = observed_property
        self.last_successful_fetch: datetime | None = None

    async def _async_update_data(self) -> Observation:
        try:
            observation = await self.client.async_get_latest_observation(
                self.offering, self.observed_property
            )
        except WupperverbandApiError as err:
            raise UpdateFailed(
                f"Error communicating with Wupperverband SOS: {err}"
            ) from err

        self.last_successful_fetch = datetime.now(UTC)
        _LOGGER.debug(
            "Fetched Wupperverband observation for %s / %s: value=%s unit=%s "
            "measurement_time=%s result_time=%s",
            self.offering,
            self.observed_property,
            observation.value,
            observation.unit,
            observation.timestamp,
            observation.result_time,
        )
        return observation

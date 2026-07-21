"""Config flow for Wupperverband Sensor Web."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    WupperverbandApiError,
    WupperverbandConnectionError,
    WupperverbandSosClient,
)
from .const import (
    CONF_DISPLAY_NAME,
    CONF_ENDPOINT,
    CONF_STALE_AFTER,
    CONF_STATION,
    CONF_TIMESERIES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ENDPOINT,
    DEFAULT_STALE_AFTER_MINUTES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_UPDATE_INTERVAL_MINUTES,
)
from .metadata_cache import async_get_metadata_cache
from .models import Station, TimeSeries


class WupperverbandConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._endpoint = DEFAULT_ENDPOINT
        self._client: WupperverbandSosClient | None = None
        self._stations: list[Station] = []
        self._selected_station: Station | None = None
        self._timeseries: list[TimeSeries] = []
        self._measurement_choices: dict[str, TimeSeries] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate endpoint and load offerings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._endpoint = user_input[CONF_ENDPOINT].strip()
            self._client = WupperverbandSosClient(
                async_get_clientsession(self.hass), self._endpoint
            )
            try:
                cache = async_get_metadata_cache(self.hass)
                self._stations = await cache.async_get_stations(self._client)
            except WupperverbandConnectionError:
                errors["base"] = "cannot_connect"
            except WupperverbandApiError:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001 - config flow must recover cleanly
                errors["base"] = "unknown"
            else:
                return await self.async_step_station()

        schema = vol.Schema(
            {
                vol.Required(CONF_ENDPOINT, default=self._endpoint): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a monitoring location."""
        errors: dict[str, str] = {}
        if user_input is not None:
            identifier = user_input[CONF_STATION]
            self._selected_station = next(
                item for item in self._stations if item.identifier == identifier
            )
            assert self._client is not None
            try:
                cache = async_get_metadata_cache(self.hass)
                self._timeseries = await cache.async_get_timeseries(
                    self._client, identifier
                )
            except WupperverbandConnectionError:
                errors["base"] = "cannot_connect"
            except WupperverbandApiError:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001 - config flow must recover cleanly
                errors["base"] = "unknown"
            else:
                return await self.async_step_property()

        options = [
            selector.SelectOptionDict(value=item.identifier, label=item.name)
            for item in self._stations
        ]
        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_property(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the measurement type and finish."""
        assert self._selected_station is not None
        self._measurement_choices = _group_measurements(self._timeseries)

        if user_input is not None:
            timeseries = self._measurement_choices[user_input[CONF_TIMESERIES]]
            display_name = user_input.get(CONF_DISPLAY_NAME, "").strip()
            unique = f"{self._endpoint}|{timeseries.identifier}"
            await self.async_set_unique_id(unique)
            self._abort_if_unique_id_configured()
            title = display_name or (
                f"{self._selected_station.name} – {timeseries.phenomenon}"
            )
            return self.async_create_entry(
                title=title,
                data={
                    CONF_ENDPOINT: self._endpoint,
                    CONF_STATION: self._selected_station.identifier,
                    CONF_TIMESERIES: timeseries.identifier,
                    CONF_DISPLAY_NAME: title,
                },
                options={
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL_MINUTES,
                    CONF_STALE_AFTER: DEFAULT_STALE_AFTER_MINUTES,
                },
            )

        if not self._measurement_choices:
            return self.async_abort(reason="no_observed_properties")

        options = [
            selector.SelectOptionDict(value=key, label=key)
            for key in self._measurement_choices
        ]
        return self.async_show_form(
            step_id="property",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TIMESERIES): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(CONF_DISPLAY_NAME, default=""): str,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return options flow."""
        return WupperverbandOptionsFlow()


class WupperverbandOptionsFlow(OptionsFlow):
    """Handle configurable polling and stale thresholds."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_UPDATE_INTERVAL_MINUTES,
                            max=MAX_UPDATE_INTERVAL_MINUTES,
                        ),
                    ),
                    vol.Required(
                        CONF_STALE_AFTER,
                        default=options.get(CONF_STALE_AFTER, DEFAULT_STALE_AFTER_MINUTES),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=10080)),
                }
            ),
        )


def _group_measurements(timeseries: list[TimeSeries]) -> dict[str, TimeSeries]:
    """Collapse raw time series into the measurement choices shown by Sensor Web."""
    grouped: dict[str, TimeSeries] = {}
    for item in timeseries:
        label = item.phenomenon.strip()
        if not label:
            continue
        current = grouped.get(label)
        if current is None or _timeseries_sort_key(item) < _timeseries_sort_key(current):
            grouped[label] = item
    return dict(sorted(grouped.items(), key=lambda entry: entry[0].casefold()))


def _timeseries_sort_key(item: TimeSeries) -> tuple[int, str, str]:
    """Prefer the least-specific series when multiple rows share one label."""
    return (
        0 if not item.procedure else 1,
        (item.procedure or "").casefold(),
        item.identifier,
    )

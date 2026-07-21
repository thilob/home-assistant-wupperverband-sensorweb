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
    humanize_identifier,
)
from .const import (
    CONF_DISPLAY_NAME,
    CONF_ENDPOINT,
    CONF_OBSERVED_PROPERTY,
    CONF_OFFERING,
    CONF_STALE_AFTER,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ENDPOINT,
    DEFAULT_STALE_AFTER_MINUTES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_UPDATE_INTERVAL_MINUTES,
)
from .models import Offering


class WupperverbandConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._endpoint = DEFAULT_ENDPOINT
        self._offerings: list[Offering] = []
        self._selected_offering: Offering | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate endpoint and load offerings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._endpoint = user_input[CONF_ENDPOINT].strip()
            client = WupperverbandSosClient(
                async_get_clientsession(self.hass), self._endpoint
            )
            try:
                self._offerings = await client.async_get_offerings()
            except WupperverbandConnectionError:
                errors["base"] = "cannot_connect"
            except WupperverbandApiError:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001 - config flow must recover cleanly
                errors["base"] = "unknown"
            else:
                return await self.async_step_offering()

        schema = vol.Schema(
            {
                vol.Required(CONF_ENDPOINT, default=self._endpoint): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_offering(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select an observation offering."""
        if user_input is not None:
            identifier = user_input[CONF_OFFERING]
            self._selected_offering = next(
                item for item in self._offerings if item.identifier == identifier
            )
            return await self.async_step_property()

        options = [
            selector.SelectOptionDict(value=item.identifier, label=item.name)
            for item in self._offerings
        ]
        return self.async_show_form(
            step_id="offering",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OFFERING): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_property(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select observed property and finish."""
        assert self._selected_offering is not None
        properties = self._selected_offering.observed_properties

        if user_input is not None:
            observed_property = user_input[CONF_OBSERVED_PROPERTY]
            display_name = user_input.get(CONF_DISPLAY_NAME, "").strip()
            unique = f"{self._endpoint}|{self._selected_offering.identifier}|{observed_property}"
            await self.async_set_unique_id(unique)
            self._abort_if_unique_id_configured()
            title = display_name or (
                f"{self._selected_offering.name} – {humanize_identifier(observed_property)}"
            )
            return self.async_create_entry(
                title=title,
                data={
                    CONF_ENDPOINT: self._endpoint,
                    CONF_OFFERING: self._selected_offering.identifier,
                    CONF_OBSERVED_PROPERTY: observed_property,
                    CONF_DISPLAY_NAME: title,
                },
                options={
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL_MINUTES,
                    CONF_STALE_AFTER: DEFAULT_STALE_AFTER_MINUTES,
                },
            )

        if not properties:
            return self.async_abort(reason="no_observed_properties")

        options = [
            selector.SelectOptionDict(value=value, label=humanize_identifier(value))
            for value in properties
        ]
        return self.async_show_form(
            step_id="property",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OBSERVED_PROPERTY): selector.SelectSelector(
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

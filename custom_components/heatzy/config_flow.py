"""Config flow to configure Heatzy."""
from __future__ import annotations

import logging

import voluptuous as vol
from wsheatzypy import HeatzyClient
from wsheatzypy.exception import (
    AuthenticationFailed,
    HeatzyException,
    HttpRequestFailed,
)

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_WEBSOCKET, DOMAIN

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)

_LOGGER = logging.getLogger(__name__)


class HeatzyFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Heatzy config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get option flow."""
        return HeatzyOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input:
            try:
                username = user_input[CONF_USERNAME]
                self._async_abort_entries_match({CONF_USERNAME: username})
                api = HeatzyClient(
                    username,
                    user_input[CONF_PASSWORD],
                    async_create_clientsession(self.hass),
                )
                await api.async_bindings()
            except AuthenticationFailed:
                errors["base"] = "invalid_auth"
            except HttpRequestFailed:
                errors["base"] = "cannot_connect"
            except HeatzyException:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"{DOMAIN} ({username})", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class HeatzyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle option."""

    def __init__(self, config_entry):
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle a flow initialized by the user."""
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_WEBSOCKET,
                    default=self.config_entry.options.get(CONF_WEBSOCKET, True),
                ): bool
            },
        )
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=options_schema)

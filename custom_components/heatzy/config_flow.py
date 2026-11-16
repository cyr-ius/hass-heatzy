"""Config flow to configure Heatzy."""

from collections.abc import Mapping
from typing import Any

from heatzypy import HeatzyClient
from heatzypy.exception import AuthenticationFailed, HeatzyException, HttpRequestFailed
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


class HeatzyFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Heatzy config flow."""

    VERSION = 1

    async def _async_validate(self, username: str, password: str) -> dict[str, str]:
        """Log in to the Heatzy cloud and return the form errors."""
        api = HeatzyClient(username, password, async_create_clientsession(self.hass))
        try:
            await api.async_bindings()
        except AuthenticationFailed:
            return {"base": "invalid_auth"}
        except HttpRequestFailed:
            return {"base": "cannot_connect"}
        except HeatzyException:
            return {"base": "unknown"}
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input:
            username = user_input[CONF_USERNAME]
            self._async_abort_entries_match({CONF_USERNAME: username})
            errors = await self._async_validate(username, user_input[CONF_PASSWORD])
            if not errors:
                return self.async_create_entry(
                    title=f"{DOMAIN} ({username})", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Start a reauthentication when the stored password is refused."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask for the new password of the account."""
        entry = self._get_reauth_entry()
        username = entry.data[CONF_USERNAME]
        errors: dict[str, str] = {}
        if user_input:
            errors = await self._async_validate(username, user_input[CONF_PASSWORD])
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={CONF_USERNAME: username},
            errors=errors,
        )

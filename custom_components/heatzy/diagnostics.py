"""Diagnostics support for Heatzy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

TO_REDACT = {
    "address",
    "api_key",
    "city",
    "country",
    "email",
    "encryption_password",
    "encryption_salt",
    "host",
    "imei",
    "ip4_addr",
    "ip6_addr",
    "password",
    "phone",
    "serial",
    "system_serial",
    "userId",
    "username",
    "mac",
    "passcode",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    bindings = await coordinator.api.async_bindings()
    devices = await coordinator.api.websocket.async_get_devices()
    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "bindings": async_redact_data(bindings, TO_REDACT),
        "devices": async_redact_data(devices, TO_REDACT),
    }

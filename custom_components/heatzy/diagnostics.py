"""Diagnostics support for Heatzy.

Read-only: it never sends a command to the modules.
"""

from typing import Any

from heatzypy import HeatzyException

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import HeatzyConfigEntry

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
    "mac",
    "passcode",
    "password",
    "phone",
    "serial",
    "system_serial",
    "token",
    "uid",
    "userId",
    "username",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HeatzyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    errors: list[str] = []

    bindings: Any = None
    try:
        bindings = await coordinator.api.async_bindings()
    except HeatzyException as err:
        errors.append(f"bindings: {err}")

    devices: Any = None
    try:
        devices = await coordinator.api.websocket.async_get_devices()
    except HeatzyException as err:
        errors.append(f"websocket devices: {err}")

    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "websocket_connected": coordinator.api.websocket.is_connected,
            "data": async_redact_data(coordinator.data, TO_REDACT),
        },
        "bindings": async_redact_data(bindings, TO_REDACT),
        "devices": async_redact_data(devices, TO_REDACT),
        "errors": errors,
    }

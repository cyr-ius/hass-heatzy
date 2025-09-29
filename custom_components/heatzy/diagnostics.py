"""Diagnostics support for Heatzy."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ATTRS, CONF_MODE

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
    api_errors = []
    api_callback = []

    def callback(data):
        api_callback.append(data)

    coordinator.api.websocket.register_callback(callback)
    try:
        for did, device in devices.items():
            old_state = device.get("attrs").get("mode")
            if old_state:
                await coordinator.api.websocket.async_control_device(
                    did, {CONF_ATTRS: {CONF_MODE: "eco"}}
                )
                await coordinator.api.websocket.async_control_device(
                    did, {CONF_ATTRS: {CONF_MODE: old_state}}
                )
    except Exception as err:  # noqa: BLE001
        api_errors.append(err)
    finally:
        await asyncio.sleep(3)
        coordinator.api.websocket.unregister_callback(callback)

    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "bindings": async_redact_data(bindings, TO_REDACT),
        "devices": async_redact_data(devices, TO_REDACT),
        "errors": api_errors,
        "calbacks": api_callback,
    }

"""Diagnostics support for Heatzy."""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from wsheatzypy import HeatzyClient

from .const import CONF_WEBSOCKET, DOMAIN

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
    coordinator = hass.data[DOMAIN][entry.entry_id]
    bindings = await coordinator.api.async_bindings()
    diag_v1 = None
    ws_mode = entry.options.get(CONF_WEBSOCKET)
    if ws_mode:
        devices = await coordinator.api.websocket.async_get_devices()
        diag_v1 = await test_diag_v1(coordinator, devices, entry, hass)

    else:
        devices = await coordinator.api.async_get_devices()

    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "bindings": async_redact_data(bindings, TO_REDACT),
        "devices": async_redact_data(devices, TO_REDACT),
        "diag_v1": diag_v1,
    }


async def test_diag_v1(coordinator, devices, entry, hass):
    """Diagonostic for Heatzy v1."""
    diag_v1 = []

    def trace_callback(data):
        diag_v1.append([data.get("did"), data.get("attrs", {}).get("mode")])

    api = HeatzyClient(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        async_create_clientsession(hass),
    )

    ws = api.websocket

    await ws.async_connect()
    event = asyncio.Event()
    task = hass.async_create_task(ws.async_listen(callback=trace_callback, event=event))
    diag_v1 = []

    for did, device in devices.items():
        if device.get("product_key") == "9420ae048da545c88fc6274d204dd25f":
            await ws.async_control_device(did, {"raw": [1, 1, 3]})
            await asyncio.sleep(2)
            device = await api.async_get_device(did)
            diag_v1.append([1, device.get("attrs", {}).get("mode")])

            await ws.async_control_device(did, {"raw": "\u505c\u6b62"})
            await asyncio.sleep(2)
            device = await api.async_get_device(did)
            diag_v1.append([2, device.get("attrs", {}).get("mode")])

            await ws.async_control_device(did, "\u505c\u6b62")
            await asyncio.sleep(2)
            device = await api.async_get_device(did)
            diag_v1.append([3, device.get("attrs", {}).get("mode")])

    await ws.async_disconnect()
    task.cancel()
    return diag_v1

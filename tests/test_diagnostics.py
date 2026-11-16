"""Tests for the Heatzy diagnostics."""

import copy
from unittest.mock import AsyncMock

from heatzypy.exception import HeatzyException
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.heatzy.diagnostics import async_get_config_entry_diagnostics
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def test_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """Return redacted data without sending any command to the modules."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    devices = copy.deepcopy(load_json_object_fixture("Devices.json"))
    HeatzyClient.websocket.async_get_devices = AsyncMock(return_value=devices)
    HeatzyClient.async_bindings = AsyncMock(
        return_value={"devices": [{"mac": "aa:bb", "did": "x", "passcode": "s"}]}
    )
    HeatzyClient.websocket.async_control_device.reset_mock()

    result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert set(result) == {"entry", "coordinator", "bindings", "devices", "errors"}
    assert result["entry"]["data"]["username"] == "**REDACTED**"
    assert result["entry"]["data"]["password"] == "**REDACTED**"
    assert result["bindings"]["devices"][0]["mac"] == "**REDACTED**"
    assert result["bindings"]["devices"][0]["passcode"] == "**REDACTED**"
    assert result["devices"]
    assert result["coordinator"]["last_update_success"] is True
    assert result["errors"] == []
    # Read-only: no command is sent to the modules.
    HeatzyClient.websocket.async_control_device.assert_not_awaited()


async def test_diagnostics_collects_errors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """Report read errors as text instead of failing."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    HeatzyClient.async_bindings = AsyncMock(side_effect=HeatzyException("down"))
    HeatzyClient.websocket.async_get_devices = AsyncMock(
        side_effect=HeatzyException("closed")
    )

    result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert result["errors"] == ["bindings: down", "websocket devices: closed"]
    assert result["bindings"] is None
    assert result["devices"] is None

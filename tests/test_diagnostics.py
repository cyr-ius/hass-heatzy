"""Tests for the Heatzy diagnostics."""

import copy
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.heatzy.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """Test diagnostics returns redacted entry, bindings and devices."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    devices = copy.deepcopy(load_json_object_fixture("Devices.json"))
    HeatzyClient.websocket.async_get_devices = AsyncMock(return_value=devices)
    HeatzyClient.async_bindings = AsyncMock(
        return_value={"devices": [{"mac": "aa:bb", "did": "x"}]}
    )

    # Invoke the registered callback so pushed updates are collected.
    HeatzyClient.websocket.register_callback = MagicMock(
        side_effect=lambda cb: cb({"update": True})
    )

    with patch(
        "custom_components.heatzy.diagnostics.asyncio.sleep", new=AsyncMock()
    ):
        result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert set(result) == {
        "entry",
        "bindings",
        "devices",
        "errors",
        "callbacks",
    }
    assert result["entry"]["data"]["username"] == "**REDACTED**"
    assert result["entry"]["data"]["password"] == "**REDACTED**"
    assert result["bindings"]["devices"][0]["mac"] == "**REDACTED**"
    assert result["devices"]
    assert result["errors"] == []
    assert result["callbacks"] == [{"update": True}]
    # Each device toggles mode twice via the websocket control.
    assert HeatzyClient.websocket.async_control_device.await_count == len(devices) * 2


async def test_diagnostics_collects_errors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """Exceptions during device control are collected in the errors list."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    devices = copy.deepcopy(load_json_object_fixture("Devices.json"))
    HeatzyClient.websocket.async_get_devices = AsyncMock(return_value=devices)
    HeatzyClient.async_bindings = AsyncMock(return_value={})
    HeatzyClient.websocket.async_control_device = AsyncMock(
        side_effect=Exception("control failed")
    )

    with patch(
        "custom_components.heatzy.diagnostics.asyncio.sleep", new=AsyncMock()
    ):
        result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert len(result["errors"]) == 1
    HeatzyClient.websocket.unregister_callback.assert_called_once()

"""Tests for the Heatzy number entities."""

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import (
    mock_restore_cache_with_extra_data,
)

from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, State


@pytest.mark.parametrize("entity_id", ["number.test_pilote_v2_vacation"])
async def test_number(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    entity_id: str,
):
    """Test number."""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == str(1)

    data = {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 2}
    await hass.services.async_call(
        Platform.NUMBER, SERVICE_SET_VALUE, data, blocking=True
    )

    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == str(2.0)


async def test_calibration(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """Test com_temp calibration offset on Glow family."""
    entity_id = "number.test_glow_temperature_calibration"

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Fixture com_temp = 8 -> offset +3 °C
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 3
    assert "device_class" not in state.attributes

    # Calibration is not exposed on Pilote Pro / Bloom
    assert hass.states.get("number.test_pilote_pro_temperature_calibration") is None
    assert hass.states.get("number.test_bloom_temperature_calibration") is None

    await hass.services.async_call(
        Platform.NUMBER,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: -2},
        blocking=True,
    )
    HeatzyClient.websocket.async_control_device.assert_awaited_with(
        "WRXYsodT9jmamVfRV8WFxy", {"attrs": {"com_temp": 3}}
    )

    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert float(hass.states.get(entity_id).state) == -2


async def test_number_restores_last_value(
    hass: HomeAssistant, config_entry: ConfigEntry, HeatzyClient: AsyncMock
) -> None:
    """Restore the vacation duration set before a restart."""
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("number.test_pilote_v2_vacation", "12"),
                {
                    "native_value": 12,
                    "native_min_value": 1,
                    "native_max_value": 255,
                    "native_step": 1,
                    "native_unit_of_measurement": "d",
                },
            )
        ],
    )
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("number.test_pilote_v2_vacation").state == "12"

import copy
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant, ServiceCall

from custom_components.heatzy.const import (
    CONF_ATTRS,
    CONF_DEROG_MODE,
    CONF_LOCK,
    CONF_WINDOW,
)


@pytest.mark.parametrize("entity_id", [ "switch.test_pilote_v2_lock"])
async def test_lock_switch(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test that the Wi-Fi switch toggles correctly."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


    # --- Test Setup ---
    coordinator = config_entry.runtime_data

    # Make a deep copy of the fixture data to allow modification in this test
    devices = copy.deepcopy(HeatzyClient.__devices)

    # Set initial state to OFF for the guest wifi
    # devices["gizrKSNGrryMk9gAjWKFD3"][CONF_ATTRS]["lock_switch"] = 0
    # HeatzyClient.__devices = devices

    # This function will be the side effect of our mock to simulate the state change
    async def mock_set_switch(device_id, data):
        devices[device_id][CONF_ATTRS][CONF_LOCK] = 1 if data[CONF_ATTRS][CONF_LOCK] == 1 else 0
        coordinator.async_set_updated_data(devices)
        await hass.async_block_till_done()

    # Configure the mock to use the side effect
    HeatzyClient.websocket.async_control_device.side_effect = mock_set_switch

    # --- Initial State Check ---
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    data = { ATTR_ENTITY_ID: entity_id }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)
    assert len(service_calls) == 1
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON

@pytest.mark.parametrize("entity_id", [ "switch.test_pilote_pro_window"])
async def test_window_switch(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test that the Wi-Fi switch toggles correctly."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    devices = copy.deepcopy(HeatzyClient.__devices)

    async def mock_set_switch(device_id, data):
        devices[device_id][CONF_ATTRS][CONF_WINDOW] = 1 if data[CONF_ATTRS][CONF_WINDOW] == 1 else 0
        coordinator.async_set_updated_data(devices)
        await hass.async_block_till_done()
    HeatzyClient.websocket.async_control_device.side_effect = mock_set_switch

    # Simulate a service call to turn the switch on
    data = { ATTR_ENTITY_ID: entity_id }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == STATE_ON

@pytest.mark.parametrize("entity_id", [ "switch.test_pilote_pro_presence_mode"])
async def test_presence_switch(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test that the Wi-Fi switch toggles correctly."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    devices = copy.deepcopy(HeatzyClient.__devices)

    async def mock_set_switch(device_id, data):
        devices[device_id][CONF_ATTRS][CONF_DEROG_MODE] = 3 if data[CONF_ATTRS][CONF_DEROG_MODE] == 3 else 0
        coordinator.async_set_updated_data(devices)
        await hass.async_block_till_done()
    HeatzyClient.websocket.async_control_device.side_effect = mock_set_switch

    # Simulate a service call to turn the switch on
    data = { ATTR_ENTITY_ID: entity_id }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    climate_state = hass.states.get('climate.test_pilote_pro')
    assert state.state == STATE_ON
    assert climate_state.state == HVACMode.AUTO
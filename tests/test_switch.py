import copy
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant, ServiceCall


async def test_lock_switch(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Test that the Wi-Fi switch toggles correctly."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


    # --- Test Setup ---
    coordinator = config_entry.runtime_data

    # Make a deep copy of the fixture data to allow modification in this test
    devices = copy.deepcopy(HeatzyClient.__devices)

    # Set initial state to OFF for the guest wifi
    devices["gizrKSNGrryMk9gAjWKFD3"]["attrs"]["lock_switch"] = 0
    HeatzyClient.__devices = devices

    # This function will be the side effect of our mock to simulate the state change on the Bbox
    async def mock_set_switch(device_id, enable):
        devices[device_id]["attrs"]["lock_switch"] = 1 if enable else 0
        coordinator.async_set_updated_data(devices)
        await hass.async_block_till_done()

    # Configure the mock to use the side effect
    HeatzyClient.websocket.async_control_device.side_effect = mock_set_switch

    # --- Initial State Check ---
    state = hass.states.get("switch.test_pilote_v2_lock")
    assert state is not None
    assert state.state == STATE_OFF

    # --- Test Turn On ---
    # Simulate a service call to turn the switch on
    data = {
        ATTR_ENTITY_ID: "switch.test_pilote_v2_lock",
    }
    await hass.services.async_call(Platform.SWITCH, "turn_on", data, blocking=True)
    assert len(service_calls) == 1
    state = hass.states.get("switch.test_pilote_v2_lock")
    assert state.state == STATE_ON


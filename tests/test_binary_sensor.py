import copy
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize("entity_id", [ "binary_sensor.test_pilote_pro_presence_detection"])
async def test_sensors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    entity_id: str,
):
    """Test that the Wi-Fi switch toggles correctly."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    devices = copy.deepcopy(HeatzyClient.__devices)
    devices["6wHqU2TvH0YUUZVhdfLhi6"]["attrs"]["derog_mode"] = 3
    devices["6wHqU2TvH0YUUZVhdfLhi6"]["attrs"]["mode"] = 'cft'
    devices["6wHqU2TvH0YUUZVhdfLhi6"]["attrs"]["cur_mode"] = 'cft'
    HeatzyClient.__devices = devices

    coordinator.async_set_updated_data(devices)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON

    devices = copy.deepcopy(HeatzyClient.__devices)
    devices["6wHqU2TvH0YUUZVhdfLhi6"]["attrs"]["derog_mode"] = 3
    devices["6wHqU2TvH0YUUZVhdfLhi6"]["attrs"]["mode"] = 'cft1'
    devices["6wHqU2TvH0YUUZVhdfLhi6"]["attrs"]["cur_mode"] = 'cft1'
    HeatzyClient.__devices = devices

    coordinator.async_set_updated_data(devices)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF 
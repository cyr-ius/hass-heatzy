import copy
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.heatzy.const import (
    CONF_ATTRS,
    CONF_CUR_MODE,
    CONF_DEROG_MODE,
    CONF_MODE,
)


@pytest.mark.parametrize("entity_id", [ "sensor.test_pilote_pro_absence_duration"])
async def test_sensors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    entity_id: str,
):
    """Test presence sensor."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = config_entry.runtime_data

    devices = copy.deepcopy(HeatzyClient.__devices)
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_DEROG_MODE] = 3
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_MODE] = 'cft'
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_CUR_MODE] = 'cft'
    HeatzyClient.__devices = devices

    coordinator.async_set_updated_data(devices)
    await hass.async_block_till_done()    

    state = hass.states.get(entity_id)
    assert state.state == "unknown"

    devices = copy.deepcopy(HeatzyClient.__devices)
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_DEROG_MODE] = 3
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_MODE] = 'cft1'
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_CUR_MODE] = 'cft1'
    HeatzyClient.__devices = devices

    coordinator.async_set_updated_data(devices)
    await hass.async_block_till_done()    

    state = hass.states.get(entity_id)
    assert state.state == '30'

    devices = copy.deepcopy(HeatzyClient.__devices)
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_DEROG_MODE] = 3
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_MODE] = 'cft2'
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_CUR_MODE] = 'cft2'
    HeatzyClient.__devices = devices

    coordinator.async_set_updated_data(devices)
    await hass.async_block_till_done()    

    state = hass.states.get(entity_id)
    assert state.state == '60'

    devices = copy.deepcopy(HeatzyClient.__devices)
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_DEROG_MODE] = 3
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_MODE] = 'eco'
    devices["6wHqU2TvH0YUUZVhdfLhi6"][CONF_ATTRS][CONF_CUR_MODE] = 'eco'
    HeatzyClient.__devices = devices

    coordinator.async_set_updated_data(devices)
    await hass.async_block_till_done()    

    state = hass.states.get(entity_id)
    assert state.state == '90'        
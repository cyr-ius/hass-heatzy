from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from homeassistant.components.climate import DOMAIN as CLIM_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall

from custom_components.heatzy.const import PRESET_COMFORT_1, PRESET_VACATION


@pytest.mark.parametrize("entity_id", [ "climate.test_pilote_v2", "climate.test_pilote_v3","climate.test_pilote_v4", "climate.test_bloom", "climate.test_pilote_pro"])
async def test_climate(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""

    with patch("custom_components.heatzy.coordinator.HeatzyDataUpdateCoordinator","async_set_updated_data"):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: HVACMode.HEAT},
    )
    assert len(service_calls) == 1
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    assert hass.states.get(entity_id).state == HVACMode.HEAT

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: HVACMode.OFF},
    )
    assert len(service_calls) == 2
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).state == HVACMode.OFF    

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: HVACMode.AUTO},
    )
    assert len(service_calls) == 3
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).state == HVACMode.AUTO    

    # Presets

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_COMFORT},
    )
    assert len(service_calls) == 4
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_COMFORT  
    
    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_AWAY},
    )
    assert len(service_calls) == 5
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_AWAY  
        

@pytest.mark.parametrize("entity_id", [ "climate.test_onix"])
async def test_onix(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""

    with patch("custom_components.heatzy.coordinator.HeatzyDataUpdateCoordinator","async_set_updated_data"):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: HVACMode.OFF},
    )
    assert len(service_calls) == 1
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).state == HVACMode.OFF   

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: HVACMode.HEAT},
    )
    assert len(service_calls) == 2
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    assert hass.states.get(entity_id).state == HVACMode.HEAT
     

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: entity_id, ATTR_TARGET_TEMP_LOW: 10, ATTR_TARGET_TEMP_HIGH:10},
    )
    assert len(service_calls) == 3
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_TARGET_TEMP_LOW] == 10.0   

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_AWAY},
    )
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_AWAY      

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_COMFORT_1},
    )
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_COMFORT_1  

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_VACATION},
    )
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_VACATION  
    assert hass.states.get(entity_id).attributes[ATTR_TARGET_TEMP_LOW] == 7.0   

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_BOOST},
    )
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_BOOST      

from unittest.mock import AsyncMock

import pytest
from homeassistant.components.climate import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
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

from custom_components.heatzy.const import (
    PRESET_COMFORT_1,
    PRESET_COMFORT_2,
    PRESET_PRESENCE_DETECT,
    PRESET_VACATION,
)


@pytest.mark.parametrize("entity_id", [ "climate.test_pilote_v2", "climate.test_pilote_v4", "climate.test_bloom", "climate.test_pilote_pro",  "climate.test_onyx"])
async def test_climate(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: HVACMode.HEAT},
    )
    assert len(service_calls) == 1
    await coordinator.async_refresh()
    assert hass.states.get(entity_id).state == HVACMode.HEAT

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: HVACMode.OFF},
    )
    assert len(service_calls) == 2
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).state == HVACMode.OFF    

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: HVACMode.AUTO},
    )
    assert len(service_calls) == 3
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
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_COMFORT  
    
    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_AWAY},
    )
    assert len(service_calls) == 5
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_AWAY 
        

@pytest.mark.parametrize("entity_id", [ "climate.test_pilote_v2", "climate.test_pilote_v4"])
async def test_derogation_vacation(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_VACATION},
    )
    assert len(service_calls) == 1
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_VACATION  

@pytest.mark.parametrize("entity_id", [ "climate.test_bloom", "climate.test_pilote_pro",  "climate.test_onyx"])
async def test_derogation_vacation_temp(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_VACATION},
    )
    assert len(service_calls) == 1
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_VACATION  
    assert hass.states.get(entity_id).attributes[ATTR_TARGET_TEMP_LOW] is not None


@pytest.mark.parametrize("entity_id", [ "climate.test_pilote_v2", "climate.test_pilote_v4", "climate.test_bloom", "climate.test_pilote_pro",  "climate.test_onyx"])
async def test_derogation_boost(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_BOOST},
    )
    assert len(service_calls) == 1
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_BOOST       

@pytest.mark.parametrize("entity_id", [ "climate.test_onyx", "climate.test_bloom", "climate.test_pilote_v4", "climate.test_pilote_pro"])
async def test_comfort1_2(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data
    
    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_COMFORT_1},
    )
    assert len(service_calls) == 1
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_COMFORT_1  
    
    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_COMFORT_2},
    )
    assert len(service_calls) == 2
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_COMFORT_2

@pytest.mark.parametrize("entity_id", ["climate.test_onyx", "climate.test_bloom"])
async def test_set_temperature(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data
    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: entity_id, ATTR_TARGET_TEMP_LOW: 10, ATTR_TARGET_TEMP_HIGH:10},
    )
    assert len(service_calls) == 1
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_TARGET_TEMP_LOW] == 10.0   


@pytest.mark.parametrize("entity_id", [ "climate.test_pilote_pro"])
async def test_derogation_presence_detect(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
    entity_id: str,
):
    """Test number"""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data

    await hass.services.async_call(
        CLIM_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: entity_id, ATTR_PRESET_MODE: PRESET_PRESENCE_DETECT},
    )
    assert len(service_calls) == 1
    await coordinator.async_refresh()
    await hass.async_block_till_done()    
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == PRESET_PRESENCE_DETECT  

@pytest.mark.parametrize("entity_id", ["climate.test_bloom", "climate.test_pilote_pro",  "climate.test_onyx"])
async def test_current_temp(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    entity_id: str,
):
    """Test number"""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes[ATTR_CURRENT_TEMPERATURE] is not None  

@pytest.mark.parametrize("entity_id", ["climate.test_pilote_pro"])
async def test_current_humidity(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    entity_id: str,
):
    """Test number"""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes[ATTR_CURRENT_HUMIDITY] is not None  


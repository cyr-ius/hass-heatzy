"""The tests for the component."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    load_json_object_fixture,
)

from custom_components.heatzy.const import (
    CONF_ATTRS,
    CONF_CUR_MODE,
    CONF_DEROG_MODE,
    CONF_DEROG_TIME,
    CONF_TIMER_SWITCH,
    DOMAIN,
)

from .const import MOCK_USER_INPUT

MODE_AUTO = {
    CONF_ATTRS: {CONF_TIMER_SWITCH: 1, CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0}
}
MODE_ON = {CONF_ATTRS: {'mode': 'cft'}}
MODE_OFF = {CONF_ATTRS: {'mode': 'stop'}}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(name="HeatzyClient")
def mock_router(request) -> Generator[MagicMock | AsyncMock]:
    """Mock a successful connection."""
    api = load_json_object_fixture("Devices.json")
    is_connected_prop = PropertyMock(return_value=False)
    is_updated_prop = PropertyMock(return_value=False)

    with patch("custom_components.heatzy.coordinator.HeatzyClient") as mock:
        instance = mock.return_value

        def _mock_register_callback(*args, **kwargs):
            if cb := kwargs.get("callback"):
                cb(api)
        instance.websocket.register_callback = MagicMock(side_effect=_mock_register_callback)

        async def _mock_connect(*args, **kwargs):
            is_connected_prop.return_value = True
        instance.websocket.async_connect = AsyncMock(side_effect=_mock_connect)

        async def _mock_listen(*args, **kwargs):
            is_updated_prop.return_value = True
            return api

        instance.websocket.async_listen = AsyncMock(side_effect=_mock_listen)
        
        async def _mock_disconnect(*args, **kwargs):
            is_connected_prop.return_value = False
        instance.websocket.async_disconnect = AsyncMock(side_effect=_mock_disconnect)

        type(instance.websocket).is_updated = is_updated_prop
        type(instance.websocket).is_connected = is_connected_prop

        def _mock_contol(*args, **kwargs):
            device = api[args[0]]
            attrs = args[1].get(CONF_ATTRS, {})
            mode= attrs.get("mode")
            
            if mode and device[CONF_ATTRS].get('cur_mode'):
                device[CONF_ATTRS][CONF_CUR_MODE] = mode      
            if mode and device[CONF_ATTRS].get('cur_signal'):                       
                device[CONF_ATTRS]['cur_signal'] = mode             
            
            device['attrs'].update(attrs)


        instance.websocket.async_control_device = AsyncMock(side_effect=_mock_contol)
        instance.async_get_devices = AsyncMock(return_value=api)
        instance.async_bindings = AsyncMock()
        type(instance).__devices = PropertyMock(return_value=api)
        yield instance


@pytest.fixture(name="config_entry")
def get_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Create and register mock config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=MOCK_USER_INPUT,
        unique_id="012345678901234",
        options={},
        title=f"{DOMAIN} ({MOCK_USER_INPUT[CONF_USERNAME]})"
    )
    config_entry.add_to_hass(hass)
    return config_entry

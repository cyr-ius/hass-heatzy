from unittest.mock import AsyncMock, patch

from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall


async def test_number(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    service_calls: list[ServiceCall],
):
    """Test number"""

    with patch("custom_components.heatzy.coordinator.HeatzyDataUpdateCoordinator","async_set_updated_data"):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    # --- Initial State Check ---
    state = hass.states.get("number.test_pilote_v2_vacation")
    assert state is not None
    assert state.state == str(1)

    data = {
        ATTR_ENTITY_ID: "number.test_pilote_v2_vacation",
        ATTR_VALUE: 2

    }
    await hass.services.async_call(Platform.NUMBER, SERVICE_SET_VALUE, data, blocking=True)

    assert len(service_calls) == 1

    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("number.test_pilote_v2_vacation")
    assert state.state == str(2.0)
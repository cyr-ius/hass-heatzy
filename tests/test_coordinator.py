"""Tests for the Heatzy coordinator."""

import asyncio
from unittest.mock import AsyncMock, PropertyMock

import pytest
from heatzypy.exception import (
    AuthenticationFailed,
    ConnectionFailed,
    HeatzyException,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.heatzy.coordinator import HeatzyDataUpdateCoordinator


async def test_setup_success(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """Test the coordinator is set up and fetches data."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = config_entry.runtime_data
    assert isinstance(coordinator, HeatzyDataUpdateCoordinator)
    assert coordinator.last_update_success is True
    # Data comes from the websocket callback registered during setup.
    assert "gizrKSNGrryMk9gAjWKFD3" in coordinator.data


async def test_update_data_polls_when_not_updated(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """Fetch via API polling when the websocket has no fresh data."""
    coordinator = HeatzyDataUpdateCoordinator(hass, config_entry)
    await coordinator._async_setup()

    # Pretend the websocket is connected (skip init) but has no update.
    type(coordinator.api.websocket).is_connected = PropertyMock(return_value=True)
    type(coordinator.api.websocket).is_updated = PropertyMock(return_value=False)

    data = await coordinator._async_update_data()
    assert "gizrKSNGrryMk9gAjWKFD3" in data
    coordinator.api.async_get_devices.assert_awaited()


async def test_update_data_returns_cached_when_updated(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """Return cached data when the websocket already pushed an update."""
    coordinator = HeatzyDataUpdateCoordinator(hass, config_entry)
    await coordinator._async_setup()

    sentinel = {"cached": True}
    coordinator.data = sentinel
    type(coordinator.api.websocket).is_connected = PropertyMock(return_value=True)
    type(coordinator.api.websocket).is_updated = PropertyMock(return_value=True)

    data = await coordinator._async_update_data()
    assert data is sentinel
    coordinator.api.async_get_devices.assert_not_awaited()


async def test_update_data_raises_update_failed(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """A HeatzyException during polling is converted to UpdateFailed."""
    coordinator = HeatzyDataUpdateCoordinator(hass, config_entry)
    await coordinator._async_setup()

    type(coordinator.api.websocket).is_connected = PropertyMock(return_value=True)
    type(coordinator.api.websocket).is_updated = PropertyMock(return_value=False)
    coordinator.api.async_get_devices = AsyncMock(
        side_effect=HeatzyException("boom")
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.parametrize(
    "error",
    [
        AuthenticationFailed("bad credentials"),
        ConnectionFailed("no route"),
        HeatzyException("unexpected"),
    ],
)
async def test_websocket_listener_errors(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
    error: Exception,
):
    """The listener marks the update as failed on websocket errors."""
    coordinator = HeatzyDataUpdateCoordinator(hass, config_entry)
    await coordinator._async_setup()
    coordinator.api.websocket.async_connect = AsyncMock(side_effect=error)

    coordinator._init_websocket()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False
    coordinator.api.websocket.async_disconnect.assert_awaited()


async def test_websocket_closed_on_hass_stop(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    HeatzyClient: AsyncMock,
):
    """The websocket is disconnected when Home Assistant stops."""
    coordinator = HeatzyDataUpdateCoordinator(hass, config_entry)
    await coordinator._async_setup()

    # Keep the listener task suspended so the stop callback drives the disconnect.
    block = asyncio.Event()

    async def _blocking_listen(*args, **kwargs):
        await block.wait()

    coordinator.api.websocket.async_listen = AsyncMock(side_effect=_blocking_listen)

    coordinator._init_websocket()
    assert coordinator.unsub is not None

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    # Release the listener so the background task can finish cleanly.
    block.set()
    await hass.async_block_till_done()

    assert coordinator.unsub is None
    coordinator.api.websocket.async_disconnect.assert_awaited()

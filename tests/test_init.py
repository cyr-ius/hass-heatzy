"""Tests for the Heatzy integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.heatzy import async_remove_config_entry_device
from custom_components.heatzy.const import DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr


async def test_unload_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, HeatzyClient: AsyncMock
) -> None:
    """Unload the entry and stop listening to Home Assistant stop."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    unsub = config_entry.runtime_data.unsub = MagicMock()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    unsub.assert_called_once()


async def test_options_update_reloads_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, HeatzyClient: AsyncMock
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    with patch.object(hass.config_entries, "async_reload") as reload:
        hass.config_entries.async_update_entry(config_entry, options={"x": 1})
        await hass.async_block_till_done()

    reload.assert_called_once_with(config_entry.entry_id)


async def test_remove_device(
    hass: HomeAssistant, config_entry: ConfigEntry, HeatzyClient: AsyncMock
) -> None:
    """Allow the user to remove a device from the entry."""
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id, identifiers={(DOMAIN, "did")}
    )
    assert await async_remove_config_entry_device(hass, config_entry, device)

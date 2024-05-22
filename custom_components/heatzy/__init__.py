"""Heatzy platform configuration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import HeatzyDataUpdateCoordinator

type HeatzyConfigEntry = ConfigEntry[HeatzyDataUpdateCoordinator]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: HeatzyConfigEntry) -> bool:
    """Set up Heatzy as config entry."""
    coordinator = HeatzyDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: HeatzyConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if entry.runtime_data.unsub:
            entry.runtime_data.unsub()

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: HeatzyConfigEntry):
    """Reload if change option."""
    await hass.config_entries.async_reload(entry.entry_id)

"""Tests for the Heatzy services."""

from unittest.mock import patch

from custom_components.heatzy.const import DOMAIN
from custom_components.heatzy.services import SERVICES
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant


async def test_services_registered_without_loaded_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Register the services at component setup, even if no entry loads."""
    with patch("custom_components.heatzy.async_setup_entry", return_value=False):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    for name, _, _ in SERVICES:
        assert hass.services.has_service(DOMAIN, name)

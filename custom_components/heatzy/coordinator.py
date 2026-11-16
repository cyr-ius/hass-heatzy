"""Coordinator Heatzy platform."""

from datetime import datetime, timedelta
import logging
from typing import Any

from heatzypy import HeatzyClient
from heatzypy.exception import AuthenticationFailed, ConnectionFailed, HeatzyException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = 60
# The websocket only learns the account modules when it connects: read the
# full list from the API regularly to add new modules and remove old ones.
FULL_REFRESH_INTERVAL = timedelta(minutes=30)


class HeatzyDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to fetch data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Class to manage fetching Heatzy data API."""
        self.entry = entry
        self.unsub: CALLBACK_TYPE | None = None
        self._last_full_refresh: datetime | None = None
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=SCAN_INTERVAL)
        )

    async def _async_setup(self) -> None:
        """Coordinator setup."""
        self.api = HeatzyClient(
            self.entry.data[CONF_USERNAME],
            self.entry.data[CONF_PASSWORD],
            async_create_clientsession(self.hass),
        )

    @callback
    def _init_websocket(self, event: Event | None = None) -> None:
        """Use WebSocket for updates, instead of polling."""

        async def async_listener() -> None:
            """Create the connection and listen to the websocket."""
            try:
                self.api.websocket.register_callback(
                    callback=self.async_set_updated_data
                )
                await self.api.websocket.async_connect(
                    auto_subscribe=True, all_devices=True
                )
                await self.api.websocket.async_listen()
            except AuthenticationFailed as error:
                self.logger.error("Authentication failed (%s)", error)
                self.last_update_success = False
                self.entry.async_start_reauth(self.hass)
            except ConnectionFailed as error:
                self.logger.error("Connection failed (%s)", error)
                self.last_update_success = False
            except HeatzyException as error:
                self.logger.error(error)
                self.last_update_success = False
            finally:
                self.async_update_listeners()

            # Ensure we are disconnected
            await self.api.websocket.async_disconnect()
            if self.unsub:
                self.unsub()
                self.unsub = None

        async def close_websocket(_: Event) -> None:
            """Close WebSocket connection."""
            self.unsub = None
            await self.api.websocket.async_disconnect()

        # Clean disconnect WebSocket on Home Assistant shutdown
        self.unsub = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, close_websocket
        )

        # Start listening
        self.entry.async_create_background_task(
            self.hass, async_listener(), "heatzy-listen"
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data."""
        if not self.api.websocket.is_connected and not self.unsub:
            self._init_websocket()

        try:
            if self._full_refresh_due() or not self.api.websocket.is_fresh(
                SCAN_INTERVAL * 2
            ):
                devices = await self.api.async_get_devices()
                self._last_full_refresh = dt_util.utcnow()
                self._async_remove_stale_devices(devices)
                return devices
        except AuthenticationFailed as error:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from error
        except HeatzyException as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error
        else:
            return self.data

    def _full_refresh_due(self) -> bool:
        """Return True when the module list must be read from the API."""
        return (
            self._last_full_refresh is None
            or dt_util.utcnow() - self._last_full_refresh >= FULL_REFRESH_INTERVAL
        )

    @callback
    def _async_remove_stale_devices(self, devices: dict[str, Any]) -> None:
        """Remove the devices of modules that left the account.

        Only called with the full list from the API; an empty list is ignored
        so that a cloud glitch never removes every device.
        """
        if not devices:
            return
        registry = dr.async_get(self.hass)
        for device in dr.async_entries_for_config_entry(registry, self.entry.entry_id):
            dids = {key for domain, key in device.identifiers if domain == DOMAIN}
            if dids and not dids & devices.keys():
                registry.async_remove_device(device.id)

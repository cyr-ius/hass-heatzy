"""Coordinator Heatzy platform."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from heatzypy import HeatzyClient
from heatzypy.exception import AuthenticationFailed, ConnectionFailed, HeatzyException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_WEBSOCKET, DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = 60


class HeatzyDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to fetch data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Class to manage fetching Heatzy data API."""
        self.unsub: CALLBACK_TYPE | None = None
        self.ws_mode = entry.options.get(CONF_WEBSOCKET)
        self.api = HeatzyClient(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            async_create_clientsession(hass),
        )
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=SCAN_INTERVAL)
        )
        self.async_control_device = self.api.async_control_device

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
        self.config_entry.async_create_background_task(
            self.hass, async_listener(), "heatzy-listen"
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data."""
        if not self.api.websocket.is_connected and not self.unsub:
            self._init_websocket()

        try:
            if not self.api.websocket.is_updated:
                return await self.api.async_get_devices()
        except HeatzyException as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error
        else:
            return self.data

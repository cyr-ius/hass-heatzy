"""Coordinator Heatzy platform."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from wsheatzypy import HeatzyClient
from wsheatzypy.exception import ConnectionClosed, HeatzyException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class HeatzyDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to fetch data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Class to manage fetching Heatzy data API."""
        self.unsub: CALLBACK_TYPE | None = None
        self.api = HeatzyClient(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            async_create_clientsession(hass),
        )
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=60)
        )

    @callback
    def _use_websocket(self, event) -> None:
        """Use WebSocket for updates, instead of polling."""

        async def listen() -> None:
            try:
                await self.api.websocket.async_connect()
            except HeatzyException as err:
                self.logger.info(err)
                if self.unsub:
                    self.unsub()
                    self.unsub = None
                return

            try:
                await self.api.websocket.async_listen(
                    callback=self.async_set_updated_data, all_devices=True, event=event
                )
            except ConnectionClosed as err:
                self.last_update_success = False
                self.logger.info(err)
            except HeatzyException as error:
                self.last_update_success = False
                self.async_update_listeners()
                self.logger.error(error)

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
            self.hass, listen(), "heatzy-listen"
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data."""
        if not self.api.is_connected and not self.unsub:
            event = asyncio.Event()
            self._use_websocket(event)
            await event.wait()

        try:
            devices = await self.api.websocket.async_get_devices()
        except HeatzyException as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error

        _LOGGER.debug(devices)
        return devices

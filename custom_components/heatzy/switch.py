"""Sensors for Heatzy."""
from __future__ import annotations

import logging

from wsheatzypy.exception import HeatzyException

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HeatzyDataUpdateCoordinator
from .const import CONF_ATTRS, CONF_LOCK, CONF_WEBSOCKET, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[LockSwitchEntity] = []
    for unique_id, device in coordinator.data.items():
        # if device.get(CONF_ATTR, {}).get(ATTR_LOCK_SWITCH) is not None:
        entities.append(LockSwitchEntity(coordinator, unique_id))
    async_add_entities(entities)


class LockSwitchEntity(CoordinatorEntity[HeatzyDataUpdateCoordinator], SwitchEntity):
    """Lock Switch."""

    entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self, coordinator: HeatzyDataUpdateCoordinator, unique_id: str
    ) -> None:
        """Initialize switch."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, unique_id)})
        self._attr = coordinator.data[unique_id].get(CONF_ATTRS, {})

        # Interim code to ensure the transition
        self._ws_mode = coordinator.config_entry.options.get(CONF_WEBSOCKET)
        if self._ws_mode:
            self.coordinator.api.async_control_device = (
                self.coordinator.api.websocket.async_control_device
            )
        # End

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._attr.get(CONF_LOCK)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("------- UPDATE SWITCH %s ------- ", self.unique_id)
        self._attr = self.coordinator.data[self.unique_id].get(CONF_ATTRS, {})
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_LOCK: 1}}
            )

            # Interim code to ensure the transition
            if not self._ws_mode:
                await self.coordinator.async_request_refresh()
            # End

        except HeatzyException as error:
            _LOGGER.error("Error to lock pilot : %s", error)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_LOCK: 0}}
            )

            # Interim code to ensure the transition
            if not self._ws_mode:
                await self.coordinator.async_request_refresh()
            # End

        except HeatzyException as error:
            _LOGGER.error("Error to lock pilot : %s", error)

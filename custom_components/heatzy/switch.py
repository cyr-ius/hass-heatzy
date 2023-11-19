"""Sensors for Heatzy."""
from __future__ import annotations

import logging

from heatzypy.exception import HeatzyException
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HeatzyDataUpdateCoordinator
from .const import ATTR_LOCK_SWITCH, CONF_ATTR, CONF_ATTRS, CONF_LOCK, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[LockSwitchEntity] = []
    for unique_id, device in coordinator.data.items():
        if device.get(CONF_ATTR, {}).get(ATTR_LOCK_SWITCH) is not None:
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

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_LOCK)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_LOCK: 1}}
            )
        except HeatzyException as error:
            _LOGGER.error("Error to lock pilot : %s", error)

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_LOCK: 0}}
            )
        except HeatzyException as error:
            _LOGGER.error("Error to lock pilot : %s", error)

        await self.coordinator.async_request_refresh()

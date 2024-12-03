"""Parent Entity."""

from __future__ import annotations

import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ALIAS, CONF_ATTRS, CONF_MODEL, CONF_VERSION, DOMAIN
from .coordinator import HeatzyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HeatzyEntity(CoordinatorEntity[HeatzyDataUpdateCoordinator], Entity):
    """Base class for all entities."""

    entity_description: EntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        description: EntityDescription,
        did: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self.did = did
        self._attr_unique_id = f"{did}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, did)},
            manufacturer=DOMAIN.capitalize(),
            sw_version=coordinator.data[did].get(CONF_VERSION),
            model=coordinator.data[did].get(CONF_MODEL),
            name=coordinator.data[did][CONF_ALIAS],
        )
        self._attrs = coordinator.data[did].get(CONF_ATTRS, {})

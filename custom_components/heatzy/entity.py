"""Parent Entity."""

import logging
from typing import Any

from heatzypy import HeatzyException
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ALIAS, CONF_ATTRS, CONF_MODEL, CONF_VERSION, DOMAIN
from .coordinator import HeatzyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HeatzyEntity(CoordinatorEntity[HeatzyDataUpdateCoordinator]):
    """Base class for all entities."""

    _attr_has_entity_name = True
    entity_description: EntityDescription

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        description: EntityDescription,
        did: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self.device_id = did
        self._attr_unique_id = f"{did}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, did)},
            manufacturer=DOMAIN.capitalize(),
            sw_version=coordinator.data[did].get(CONF_VERSION),
            model=coordinator.data[did].get(CONF_MODEL),
            name=coordinator.data[did][CONF_ALIAS],
        )
        self._device = coordinator.data.get(did, {})
        self._attrs = self._device.get(CONF_ATTRS, {})
        self.async_control_device = coordinator.api.websocket.async_control_device

    async def _handle_action(
        self, config: dict[str, Any], error_msg: str = "Error unknown"
    ):
        """Execute action."""
        try:
            _LOGGER.debug("Handle action (%s): %s", self.device_id, config)
            await self.async_control_device(self.device_id, config)
        except HeatzyException as error:
            _LOGGER.error("%s (%s)", error_msg, error)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._device = self.coordinator.data.get(self.device_id, {})
        self._attrs = self._device.get(CONF_ATTRS, {})
        super()._handle_coordinator_update()

"""Parent Entity."""

from collections.abc import Callable, Iterable
import logging
from typing import Any

from heatzypy import HeatzyException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ALIAS,
    CONF_ATTRS,
    CONF_IS_ONLINE,
    CONF_MODEL,
    CONF_VERSION,
    DOMAIN,
)
from .coordinator import HeatzyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

type EntityBuilder = Callable[
    [HeatzyDataUpdateCoordinator, str, dict[str, Any]], Iterable[Entity]
]


@callback
def async_setup_device_entities(
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    build: EntityBuilder,
) -> None:
    """Add the entities of each module, also for modules added to the account later.

    build returns the entities of one module (did, device data).
    """
    coordinator: HeatzyDataUpdateCoordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _async_add_new_devices() -> None:
        if new := set(coordinator.data or {}) - known:
            known.update(new)
            async_add_entities(
                [
                    entity
                    for did in sorted(new)
                    for entity in build(coordinator, did, coordinator.data[did])
                ]
            )

    _async_add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_devices))


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

    @property
    def available(self) -> bool:
        """Return True if the coordinator is healthy and the device is online."""
        return super().available and bool(self._device.get(CONF_IS_ONLINE, True))

    async def _handle_action(self, config: dict[str, Any]) -> None:
        """Send a command to the module.

        Raises HomeAssistantError so that the user sees why the action failed.
        """
        _LOGGER.debug("Handle action (%s): %s", self.device_id, config)
        try:
            await self.async_control_device(self.device_id, config)
        except HeatzyException as error:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={
                    "device": self._device.get(CONF_ALIAS, self.device_id),
                    "error": str(error),
                },
            ) from error

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._device = self.coordinator.data.get(self.device_id, {})
        self._attrs = self._device.get(CONF_ATTRS, {})
        super()._handle_coordinator_update()

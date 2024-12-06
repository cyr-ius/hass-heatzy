"""Sensors for Heatzy."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Final

from heatzypy.exception import HeatzyException

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatzyConfigEntry, HeatzyDataUpdateCoordinator
from .const import CONF_ATTRS, CONF_LOCK, CONF_WINDOW
from .entity import HeatzyEntity


@dataclass(frozen=True)
class HeatzySwitchEntityDescription(SwitchEntityDescription):
    """Represents an Flow Sensor."""

    attr: str | None = None


SWITCH_TYPES: Final[tuple[HeatzySwitchEntityDescription, ...]] = (
    HeatzySwitchEntityDescription(
        key="lock",
        name="Lock",
        translation_key="lock",
        attr=CONF_LOCK,
        entity_category=EntityCategory.CONFIG,
    ),
    HeatzySwitchEntityDescription(
        key="window",
        name="Window",
        icon="mdi:window-open-variant",
        translation_key="window",
        attr=CONF_WINDOW,
        entity_category=EntityCategory.CONFIG,
    ),
)
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatzyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set the sensor platform."""
    coordinator = entry.runtime_data
    entities = []

    for unique_id, device in coordinator.data.items():
        for description in SWITCH_TYPES:
            if device.get(CONF_ATTRS, {}).get(description.attr) is not None:
                entities.extend([SwitchEntity(coordinator, description, unique_id)])
    async_add_entities(entities)


class SwitchEntity(HeatzyEntity, SwitchEntity):
    """Switch."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: HeatzyDataUpdateCoordinator, description, did: str
    ) -> None:
        """Initialize switch."""
        super().__init__(coordinator, description, did)

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._attrs.get(self.entity_description.attr) == 1

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        try:
            await self.async_control_device(
                self.unique_id, {CONF_ATTRS: {self.entity_description.attr: 1}}
            )
        except HeatzyException as error:
            _LOGGER.error("Error to action : %s", error)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        try:
            await self.async_control_device(
                self.unique_id, {CONF_ATTRS: {self.entity_description.attr: 0}}
            )
        except HeatzyException as error:
            _LOGGER.error("Error to action : %s", error)

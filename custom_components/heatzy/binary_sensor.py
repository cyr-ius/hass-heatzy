"""Sensor for heatzy."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.climate import PRESET_COMFORT
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatzyDataUpdateCoordinator
from .const import CONF_CUR_MODE, CONF_DEROG_MODE, CONF_PRODUCT_KEY, PILOTE_PRO_V1
from .entity import HeatzyEntity


@dataclass(frozen=True, kw_only=True)
class HeatzyBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Represents an Flow Sensor."""

    attr: str | None = None
    cls: Callable[..., Any] | None = None


PRESENCE_TYPES: Final[tuple[HeatzyBinarySensorEntityDescription, ...]] = (
    HeatzyBinarySensorEntityDescription(
        key="presence_enabled",
        name="Presence mode",
        translation_key="presence_enabled",
        cls=lambda *args: PresenceActivate(*args),
        icon="mdi:motion-sensor",
    ),
    HeatzyBinarySensorEntityDescription(
        key="presence_detected",
        name="Presence",
        translation_key="presence_detected",
        cls=lambda *args: PresenceDetect(*args),
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        icon="mdi:location-enter",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    entities = []

    for unique_id, device in coordinator.data.items():
        product_key = device.get(CONF_PRODUCT_KEY)
        if product_key in PILOTE_PRO_V1:
            for description in PRESENCE_TYPES:
                if cls := description.cls:
                    entities.extend([cls(coordinator, description, unique_id)])

    async_add_entities(entities)


class PresenceActivate(HeatzyEntity, BinarySensorEntity):
    """Heatzy presence."""

    entity_description: HeatzyBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        description: HeatzyBinarySensorEntityDescription,
        did: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, did)

    @property
    def is_on(self) -> bool:
        """Presence status."""
        return self._attrs.get(CONF_DEROG_MODE) == 3


class PresenceDetect(HeatzyEntity, BinarySensorEntity):
    """Heatzy presence."""

    entity_description: HeatzyBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        description: HeatzyBinarySensorEntityDescription,
        did: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, did)

    @property
    def is_on(self) -> bool:
        """Presence status."""
        return (
            self._attrs.get(CONF_DEROG_MODE) == 3
            and self._attrs.get(CONF_CUR_MODE) == PRESET_COMFORT
        )

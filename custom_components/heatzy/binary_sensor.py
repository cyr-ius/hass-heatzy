"""Sensor for heatzy."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CUR_MODE, CONF_DEROG_MODE, CONF_PRODUCT_KEY, PILOTE_PRO_V1
from .entity import HeatzyEntity


@dataclass(frozen=True, kw_only=True)
class HeatzyBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Represents an Flow Sensor."""

    products: list[str]
    value_fn: Callable[..., Any]
    cls: Callable[..., Any] = lambda *args: HeatzyBinarySensor(*args)


BINARY_SENSOR_TYPES: Final[tuple[HeatzyBinarySensorEntityDescription, ...]] = (
    HeatzyBinarySensorEntityDescription(
        key="presence_detected",
        name="Presence detection",
        translation_key="presence_detected",
        products=PILOTE_PRO_V1,
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        icon="mdi:location-enter",
        value_fn=lambda attrs: attrs.get(CONF_DEROG_MODE) == 3
        and attrs.get(CONF_CUR_MODE) == "cft",
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
        for description in BINARY_SENSOR_TYPES:
            cls = description.cls
            if product_key in description.products:
                entities.extend([cls(coordinator, description, unique_id)])

    async_add_entities(entities)


class HeatzyBinarySensor(HeatzyEntity, BinarySensorEntity):
    """Heatzy presence."""

    entity_description: HeatzyBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Presence status."""
        return self.entity_description.value_fn(self._attrs)

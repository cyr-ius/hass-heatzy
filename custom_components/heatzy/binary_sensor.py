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
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CUR_MODE,
    CONF_DEROG_MODE,
    CONF_IS_ONLINE,
    CONF_PRODUCT_KEY,
    PILOTE_PRO_V1,
)
from .entity import HeatzyEntity

# Data comes from the coordinator; actions are not limited.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class HeatzyBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Represents an Flow Sensor."""

    # None means the sensor applies to every product.
    products: list[str] | None
    value_fn: Callable[..., Any]
    cls: Callable[..., Any] = lambda *args: HeatzyBinarySensor(*args)


BINARY_SENSOR_TYPES: Final[tuple[HeatzyBinarySensorEntityDescription, ...]] = (
    HeatzyBinarySensorEntityDescription(
        key="presence_detected",
        translation_key="presence_detected",
        products=PILOTE_PRO_V1,
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda device: (
            device.get("attrs", {}).get(CONF_DEROG_MODE) == 3
            and device.get("attrs", {}).get(CONF_CUR_MODE) == "cft"
        ),
    ),
    HeatzyBinarySensorEntityDescription(
        key="connectivity",
        translation_key="connectivity",
        products=None,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: bool(device.get(CONF_IS_ONLINE, True)),
        cls=lambda *args: HeatzyConnectivitySensor(*args),
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
        entities.extend(
            description.cls(coordinator, description, unique_id)
            for description in BINARY_SENSOR_TYPES
            if description.products is None or product_key in description.products
        )

    async_add_entities(entities)


class HeatzyBinarySensor(HeatzyEntity, BinarySensorEntity):
    """Heatzy binary sensor."""

    entity_description: HeatzyBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Return sensor state."""
        return self.entity_description.value_fn(self._device)


class HeatzyConnectivitySensor(HeatzyBinarySensor):
    """Cloud connectivity of a Heatzy module.

    Stays available while the module is offline so that it can report it.
    """

    @property
    def available(self) -> bool:
        """Only depend on the coordinator, not on the device online status."""
        return self.coordinator.last_update_success

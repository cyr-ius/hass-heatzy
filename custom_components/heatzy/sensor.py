"""Sensor for heatzy."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CUR_MODE, CONF_DEROG_MODE, CONF_PRODUCT_KEY, PILOTE_PRO_V1
from .entity import HeatzyEntity


@dataclass(frozen=True, kw_only=True)
class HeatzySensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    attr: str | None = None
    products: list[str]
    cls: Callable[..., Any]


SENSORS_TYPE: Final[tuple[HeatzySensorEntityDescription, ...]] = (
    HeatzySensorEntityDescription(
        key="absence",
        name="Absence duration",
        translation_key="absence",
        products=PILOTE_PRO_V1,
        icon="mdi:location-exit",
        device_class=SensorDeviceClass.DURATION,
        cls=lambda *args: PresenceSensor(*args),
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
        for description in SENSORS_TYPE:
            cls = description.cls
            if product_key in description.products:
                entities.extend([cls(coordinator, description, unique_id)])

    async_add_entities(entities)


class PresenceSensor(HeatzyEntity, SensorEntity):
    """Heatzy presence."""

    entity_description: HeatzySensorEntityDescription

    @property
    def native_value(self) -> int | None:
        """Presence status."""
        if (
            self._attrs.get(CONF_DEROG_MODE) == 3
            and self._attrs.get(CONF_CUR_MODE) == "cft1"
        ):
            return 30
        if (
            self._attrs.get(CONF_DEROG_MODE) == 3
            and self._attrs.get(CONF_CUR_MODE) == "cft2"
        ):
            return 60
        if (
            self._attrs.get(CONF_DEROG_MODE) == 3
            and self._attrs.get(CONF_CUR_MODE) == "eco"
        ):
            return 90
        return None

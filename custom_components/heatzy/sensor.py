"""Sensor platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Final

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import HeatzyConfigEntry, HeatzyDataUpdateCoordinator
from .const import CONF_ATTRS, CONF_HUMIDITY
from .entity import HeatzyEntity


@dataclass(frozen=True)
class HeatzySensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    attr: str | None = None


SENSOR_TYPES: Final[tuple[HeatzySensorEntityDescription, ...]] = (
    HeatzySensorEntityDescription(
        key="humidity",
        name="Humidity",
        icon="mdi:water-percent",
        translation_key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        attr=CONF_HUMIDITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatzyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform."""
    coordinator = entry.runtime_data
    entities = []
    for unique_id, device in coordinator.data.items():
        for description in SENSOR_TYPES:
            if device.get(CONF_ATTRS, {}).get(description.attr) is not None:
                entities.extend([Sensor(coordinator, description, unique_id)])

    async_add_entities(entities)


class Sensor(HeatzyEntity, SensorEntity):
    """Sensor."""

    _attr_has_entity_name = True
    entity_description: HeatzySensorEntityDescription

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        description: HeatzySensorEntityDescription,
        did: str,
    ) -> None:
        """Initialize switch."""
        super().__init__(coordinator, description, did)

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self._attrs.get(self.entity_description.attr)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attrs = self.coordinator.data.get(self.unique_id, {}).get(CONF_ATTRS, {})
        self.async_write_ha_state()

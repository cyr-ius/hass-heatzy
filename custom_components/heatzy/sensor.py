"""Sensor platform."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HeatzyConfigEntry, HeatzyDataUpdateCoordinator
from .const import CONF_ATTRS, CONF_HUMIDITY, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatzyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform."""
    coordinator = entry.runtime_data
    entities = []
    for unique_id, device in coordinator.data.items():
        if device.get(CONF_ATTRS, {}).get(CONF_HUMIDITY) is not None:
            entities.append(HumiditySensor(coordinator, unique_id))

    async_add_entities(entities)


class HumiditySensor(CoordinatorEntity[HeatzyDataUpdateCoordinator], SensorEntity):
    """Humidity sensor."""

    _attr_has_entity_name = True
    _attr_name = "Humidity"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water-percent"

    def __init__(
        self, coordinator: HeatzyDataUpdateCoordinator, unique_id: str
    ) -> None:
        """Initialize switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"humidity_{unique_id}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, unique_id)})
        self._attr = coordinator.data[unique_id].get(CONF_ATTRS, {})

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self._attr.get(CONF_HUMIDITY)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr = self.coordinator.data[self.unique_id].get(CONF_ATTRS, {})
        self.async_write_ha_state()

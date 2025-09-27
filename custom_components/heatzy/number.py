"""Number platform."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntityDescription,
    RestoreNumber,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatzyConfigEntry, HeatzyDataUpdateCoordinator
from .const import CONF_ATTRS, CONF_DEROG_MODE
from .entity import HeatzyEntity


@dataclass(frozen=True)
class HeatzyNumberEntityDescription(NumberEntityDescription):
    """Represents an Flow Sensor."""

    attr: str = CONF_DEROG_MODE


NUMBER_TYPES: Final[tuple[HeatzyNumberEntityDescription, ...]] = (
    HeatzyNumberEntityDescription(
        key="vacation",
        name="Vacation",
        icon="mdi:island",
        translation_key="vacation",
        device_class=NumberDeviceClass.DURATION,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.DAYS,
        native_min_value=1,
        native_max_value=255,
    ),
    HeatzyNumberEntityDescription(
        key="boost",
        name="Boost",
        icon="mdi:thermometer-high",
        translation_key="boost",
        device_class=NumberDeviceClass.DURATION,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=1,
        native_max_value=255,
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
        for description in NUMBER_TYPES:
            if device.get(CONF_ATTRS, {}).get(description.attr) is not None:
                entities.extend([Number(coordinator, description, unique_id)])
    async_add_entities(entities)


class Number(HeatzyEntity, RestoreNumber):
    """Number entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        description: HeatzyNumberEntityDescription,
        did: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, did)
        self._resolve_state = 1

    @property
    def native_value(self) -> int:
        """Return the value reported by the sensor."""
        return self._resolve_state

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        if (
            last_state := await self.async_get_last_state()
        ) and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            last_number_data = await self.async_get_last_number_data()
            self._resolve_state = last_number_data.native_value

    async def async_set_native_value(self, value: int) -> None:
        """Set new value."""
        self._device[self.entity_description.key] = value
        self._resolve_state = value
        self.async_write_ha_state()

"""Sensor for heatzy."""

from dataclasses import dataclass

from homeassistant.components.climate import PRESET_ECO
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatzyDataUpdateCoordinator
from .const import (
    CONF_CUR_MODE,
    CONF_DEROG_MODE,
    CONF_PRODUCT_KEY,
    PILOTE_PRO_V1,
    PRESET_COMFORT_1,
    PRESET_COMFORT_2,
)
from .entity import HeatzyEntity


@dataclass(frozen=True, kw_only=True)
class HeatzySensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    attr: str | None = None


ABSENCE = HeatzySensorEntityDescription(
    key="absence",
    name="Absence duration",
    translation_key="absence",
    icon="mdi:location-exit",
    device_class=SensorDeviceClass.DURATION,
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
            entities.extend([PresenceSensor(coordinator, ABSENCE, unique_id)])

    async_add_entities(entities)


class PresenceSensor(HeatzyEntity, SensorEntity):
    """Heatzy presence."""

    entity_description: HeatzySensorEntityDescription

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        description: HeatzySensorEntityDescription,
        did: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, description, did)

    @property
    def native_value(self) -> int | None:
        """Presence status."""
        if (
            self._attrs.get(CONF_DEROG_MODE) == 3
            and self._attrs.get(CONF_CUR_MODE) == PRESET_COMFORT_1
        ):
            return 30
        if (
            self._attrs.get(CONF_DEROG_MODE) == 3
            and self._attrs.get(CONF_CUR_MODE) == PRESET_COMFORT_2
        ):
            return 60
        if (
            self._attrs.get(CONF_DEROG_MODE) == 3
            and self._attrs.get(CONF_CUR_MODE) == PRESET_ECO
        ):
            return 90
        return None

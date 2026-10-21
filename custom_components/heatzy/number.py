"""Number platform."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.climate import PRESET_BOOST
from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    RestoreNumber,
)
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatzyConfigEntry, HeatzyDataUpdateCoordinator
from .const import (
    ALL,
    CALIBRATION_PRODUCTS,
    CONF_ATTRS,
    CONF_COM_TEMP,
    CONF_PRODUCT_KEY,
    PRESET_VACATION,
)
from .entity import HeatzyEntity


@dataclass(frozen=True, kw_only=True)
class HeatzyNumberEntityDescription(NumberEntityDescription):
    """Represents an Flow Sensor."""

    attr: str
    products: list[str]
    cls: Callable[..., Any] = lambda *args: HeatzyNumber(*args)


NUMBER_TYPES: Final[tuple[HeatzyNumberEntityDescription, ...]] = (
    HeatzyNumberEntityDescription(
        key="vacation",
        name="Vacation",
        icon="mdi:island",
        translation_key="vacation",
        products=ALL,
        device_class=NumberDeviceClass.DURATION,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.DAYS,
        native_min_value=1,
        native_max_value=255,
        attr = PRESET_VACATION
    ),
    HeatzyNumberEntityDescription(
        key="boost",
        name="Boost",
        icon="mdi:thermometer-high",
        products=ALL,
        translation_key="boost",
        device_class=NumberDeviceClass.DURATION,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=1,
        native_max_value=255,
        attr= PRESET_BOOST
    ),
    HeatzyNumberEntityDescription(
        key="calibration",
        name="Temperature calibration",
        icon="mdi:thermometer-lines",
        translation_key="calibration",
        products=CALIBRATION_PRODUCTS,
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-5,
        native_max_value=5,
        attr=CONF_COM_TEMP,
        cls=lambda *args: HeatzyCalibrationNumber(*args),
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
        product_key = device.get(CONF_PRODUCT_KEY)
        for description in NUMBER_TYPES:
            cls = description.cls
            if product_key in description.products:
                entities.extend([cls(coordinator, description, unique_id)])
    async_add_entities(entities)


class HeatzyNumber(HeatzyEntity, RestoreNumber):
    """Number entity."""

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
    def native_value(self) -> float | None:
        """Return the value reported by the sensor."""
        return self._resolve_state

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        if (
            last_state := await self.async_get_last_state()
        ) and last_state.state not in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            last_number_data = await self.async_get_last_number_data()
            if last_number_data:
                self._resolve_state = last_number_data.native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        self._device[self.entity_description.attr] = value
        self._resolve_state = value
        self.async_write_ha_state()


class HeatzyCalibrationNumber(HeatzyEntity, NumberEntity):
    """Sensor temperature calibration offset (com_temp), pushed to the device.

    Glow family: com_temp is an int 0..10 in whole degrees, centred at 5:
    0 = -5 C, 5 = 0 C (no correction), 10 = +5 C.
    """

    @property
    def native_value(self) -> float | None:
        """Return the current calibration offset in degrees Celsius."""
        raw = self._attrs.get(self.entity_description.attr)
        return None if raw is None else raw - 5

    async def async_set_native_value(self, value: float) -> None:
        """Push the new calibration offset to the device."""
        raw = round(value) + 5
        await self._handle_action(
            {CONF_ATTRS: {self.entity_description.attr: raw}},
            "Error setting temperature calibration",
        )
        self.async_write_ha_state()

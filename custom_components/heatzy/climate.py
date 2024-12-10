"""Climate sensors for Heatzy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from typing import Any, Final

import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import CONF_DELAY, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatzyConfigEntry, HeatzyDataUpdateCoordinator
from .const import (
    BLOOM,
    CFT_TEMP_H,
    CFT_TEMP_L,
    CONF_ATTRS,
    CONF_CFT_TEMP,
    CONF_CUR_MODE,
    CONF_CUR_TEMP,
    CONF_DEROG_MODE,
    CONF_DEROG_TIME,
    CONF_ECO_TEMP,
    CONF_HEATING_STATE,
    CONF_HUMIDITY,
    CONF_IS_ONLINE,
    CONF_MODE,
    CONF_ON_OFF,
    CONF_PRODUCT_KEY,
    CONF_TIMER_SWITCH,
    CUR_TEMP_L,
    DEFAULT_BOOST,
    DEFAULT_VACATION,
    ECO_TEMP_H,
    ECO_TEMP_L,
    FROST_TEMP,
    GLOW,
    PILOTE_PRO_V1,
    PILOTE_V1,
    PILOTE_V2,
    PILOTE_V3,
    PILOTE_V4,
    PRESET_COMFORT_1,
    PRESET_COMFORT_2,
    PRESET_PRESENCE_DETECT,
    PRESET_VACATION,
)
from .entity import HeatzyEntity

SERVICES = [
    ["boost", {vol.Required(CONF_DELAY): cv.positive_int}, "_async_boost_mode"],
    ["vacation", {vol.Required(CONF_DELAY): cv.positive_int}, "_async_vacation_mode"],
    ["presence", {}, "_async_presence_detection"],
]


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeatzyClimateEntityDescription(ClimateEntityDescription):
    """Represents an Flow Sensor."""

    current_temperature: float | int | None = None
    eco_temperature_high: float | int | None = None
    eco_temperature_low: float | int | None = None
    fn: Callable[..., Any] | None = None
    ha_to_heatzy_state: dict[int | str, str | int | list[int]] | None = None
    heatzy_to_ha_state: dict[int | str, str] | None = None
    hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
    preset_modes: list[str] = field(default_factory=list)
    products: list[str] | None = None
    attr_stop: str = CONF_MODE
    value_stop: str = "stop"
    supported_features: tuple[ClimateEntityFeature] = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    target_temperature_step: float | int | None = None
    temperature_high: float | int | None = None
    temperature_low: float | int | None = None
    temperature_unit = UnitOfTemperature.CELSIUS


CLIMATE_TYPES: Final[tuple[HeatzyClimateEntityDescription, ...]] = (
    HeatzyClimateEntityDescription(
        key="pilote_v1",
        translation_key="pilote_v1",
        fn=lambda x, y, z: HeatzyPiloteV1Thermostat(x, y, z),
        products=PILOTE_V1,
        preset_modes=[
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_BOOST,
            PRESET_VACATION,
        ],
        heatzy_to_ha_state={
            "\u8212\u9002": PRESET_COMFORT,
            "\u7ecf\u6d4e": PRESET_ECO,
            "\u89e3\u51bb": PRESET_AWAY,
            "\u505c\u6b62": PRESET_NONE,
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: [1, 1, 0],
            PRESET_ECO: [1, 1, 1],
            PRESET_AWAY: [1, 1, 2],
            PRESET_NONE: [1, 1, 3],
        },
        value_stop="\u505c\u6b62",
    ),
    HeatzyClimateEntityDescription(
        key="pilote_v2",
        translation_key="pilote_v2",
        products=PILOTE_V2 + PILOTE_V3,
        preset_modes=[
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_BOOST,
            PRESET_VACATION,
        ],
        fn=lambda x, y, z: HeatzyPiloteV2Thermostat(x, y, z),
        heatzy_to_ha_state={
            "cft": PRESET_COMFORT,
            "eco": PRESET_ECO,
            "fro": PRESET_AWAY,
            "stop": PRESET_NONE,
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
            PRESET_NONE: "stop",
        },
    ),
    HeatzyClimateEntityDescription(
        key="pilote_v4",
        translation_key="pilote_v4",
        products=PILOTE_V4,
        fn=lambda x, y, z: HeatzyPiloteV3Thermostat(x, y, z),
        preset_modes=[
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_COMFORT_1,
            PRESET_COMFORT_2,
            PRESET_BOOST,
            PRESET_VACATION,
        ],
        heatzy_to_ha_state={
            "cft": PRESET_COMFORT,
            "eco": PRESET_ECO,
            "fro": PRESET_AWAY,
            "cft1": PRESET_COMFORT_1,
            "cft2": PRESET_COMFORT_2,
            "stop": PRESET_NONE,
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
            PRESET_COMFORT_1: "cft1",
            PRESET_COMFORT_2: "cft2",
            PRESET_NONE: "stop",
        },
    ),
    HeatzyClimateEntityDescription(
        key="glow",
        translation_key="glow",
        products=GLOW,
        preset_modes=[
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_COMFORT_1,
            PRESET_COMFORT_2,
            PRESET_BOOST,
            PRESET_VACATION,
        ],
        fn=lambda x, y, z: Glowv1Thermostat(x, y, z),
        supported_features=(
            ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        ),
        heatzy_to_ha_state={
            0: PRESET_COMFORT,
            1: PRESET_ECO,
            2: PRESET_AWAY,
            3: PRESET_NONE,
            4: PRESET_COMFORT_1,
            5: PRESET_COMFORT_2,
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
            PRESET_NONE: "stop",
        },
        attr_stop=CONF_ON_OFF,
        value_stop=0,
        current_temperature=CUR_TEMP_L,
        temperature_high=CFT_TEMP_H,
        temperature_low=CFT_TEMP_L,
        eco_temperature_high=ECO_TEMP_H,
        eco_temperature_low=ECO_TEMP_L,
        target_temperature_step=0.1,
    ),
    HeatzyClimateEntityDescription(
        key="bloom",
        translation_key="bloom",
        products=BLOOM,
        preset_modes=[
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_BOOST,
            PRESET_VACATION,
        ],
        fn=lambda x, y, z: Bloomv1Thermostat(x, y, z),
        supported_features=(
            ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        ),
        heatzy_to_ha_state={
            "cft": PRESET_COMFORT,
            "eco": PRESET_ECO,
            "fro": PRESET_AWAY,
            "cft1": PRESET_COMFORT_1,
            "cft2": PRESET_COMFORT_2,
            "stop": PRESET_NONE,
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
            PRESET_COMFORT_1: "cft1",
            PRESET_COMFORT_2: "cft2",
            PRESET_NONE: "stop",
        },
        current_temperature=CONF_CUR_TEMP,
        temperature_high=CONF_CFT_TEMP,
        temperature_low=CONF_ECO_TEMP,
        target_temperature_step=0.1,
    ),
    HeatzyClimateEntityDescription(
        key="pilotepro_v1",
        translation_key="pilotepro_v1",
        products=PILOTE_PRO_V1,
        fn=lambda x, y, z: HeatzyPiloteProV1(x, y, z),
        preset_modes=[
            PRESET_BOOST,
            PRESET_PRESENCE_DETECT,
            PRESET_VACATION,
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_COMFORT_1,
            PRESET_COMFORT_2,
        ],
        supported_features=(
            ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        ),
        heatzy_to_ha_state={
            "cft": PRESET_COMFORT,
            "eco": PRESET_ECO,
            "fro": PRESET_AWAY,
            "cft1": PRESET_COMFORT_1,
            "cft2": PRESET_COMFORT_2,
            "stop": PRESET_NONE,
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
            PRESET_COMFORT_1: "cft1",
            PRESET_COMFORT_2: "cft2",
            PRESET_NONE: "stop",
        },
        current_temperature=CONF_CUR_TEMP,
        temperature_high=CONF_CFT_TEMP,
        temperature_low=CONF_ECO_TEMP,
        target_temperature_step=0.1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatzyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Load all Heatzy devices."""
    coordinator = entry.runtime_data

    platform = entity_platform.async_get_current_platform()
    for service in SERVICES:
        platform.async_register_entity_service(*service)

    entities: list[HeatzyThermostat] = []
    for unique_id, device in coordinator.data.items():
        product_key = device.get(CONF_PRODUCT_KEY)
        for description in CLIMATE_TYPES:
            if product_key in description.products:
                entities.extend([description.fn(coordinator, description, unique_id)])

    async_add_entities(entities)


class HeatzyThermostat(HeatzyEntity, ClimateEntity):
    """Heatzy climate."""

    _attr_name = None
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        entity_description: HeatzyClimateEntityDescription,
        did: str,
    ) -> None:
        """Init."""
        super().__init__(coordinator, entity_description, did)
        self._attr_unique_id = did
        self._attr_temperature_unit = entity_description.temperature_unit
        self._attr_supported_features = entity_description.supported_features
        self._attr_preset_modes = entity_description.preset_modes
        self._attr_hvac_modes = entity_description.hvac_modes
        self._attr_available = coordinator.data[did].get(CONF_IS_ONLINE, True)

    @property
    def current_temperature(self) -> float:
        """The current temperature."""

    @property
    def target_temperature(self) -> float:
        """The temperature currently set to be reached."""

    @property
    def hvac_action(self) -> HVACAction:
        """Return hvac action ie. heating, off mode."""
        if self._attrs.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.target_temperature and (
            self.current_temperature > self.target_temperature
        ):
            return HVACAction.OFF
        return HVACAction.HEATING

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac mode ie. heat, auto, off."""
        _get_attr_stop = self._attrs.get(self.entity_description.attr_stop)
        _value_stop = self.entity_description.value_stop
        if self._attrs.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO
        if _get_attr_stop == _value_stop:
            return HVACMode.OFF

        return HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        if self._attrs.get(CONF_DEROG_MODE) == 1:
            return PRESET_VACATION
        if self._attrs.get(CONF_DEROG_MODE) == 2:
            return PRESET_BOOST
        if self._attrs.get(CONF_DEROG_MODE) == 3:
            return PRESET_PRESENCE_DETECT

        return self.entity_description.heatzy_to_ha_state.get(
            self._attrs.get(CONF_MODE)
        )

    async def async_turn_on(self) -> None:
        """Turn device on."""
        await self._async_derog_mode_off()
        await self.async_set_preset_mode(PRESET_COMFORT)

    async def async_turn_off(self) -> None:
        """Turn device off."""
        await self._async_derog_mode_off()
        await self.async_set_preset_mode(PRESET_NONE)

    async def async_turn_auto(self) -> None:
        """Presence detection derog."""
        config = {
            CONF_ATTRS: {CONF_TIMER_SWITCH: 1, CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0}
        }
        await self._handle_action(config, "Error while turn auto")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        elif hvac_mode == HVACMode.AUTO:
            await self.async_turn_auto()
        elif hvac_mode == HVACMode.HEAT:
            await self.async_turn_on()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if await self._async_derog_mode_action(preset_mode) is False:
            mode = self.entity_description.ha_to_heatzy_state.get(preset_mode)
            config = {CONF_ATTRS: {CONF_MODE: mode}}
            if self._attrs.get(CONF_DEROG_MODE, 0) > 0:
                config[CONF_ATTRS].update({CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0})
            await self._handle_action(config, f"Error preset mode: {preset_mode}")

    async def _async_derog_mode(self, mode: int, delay: int | None = None) -> None:
        """Derogation mode."""
        config: dict[str, Any] = {CONF_ATTRS: {CONF_DEROG_MODE: mode}}
        if delay:
            config[CONF_ATTRS][CONF_DEROG_TIME] = delay
        await self._handle_action(config, f"Error to set derog mode:{mode}")

    async def _async_derog_mode_off(self) -> None:
        """Disable derog mode."""
        if (
            self._attrs.get(CONF_DEROG_MODE, 0) > 0
            or self._attrs.get(CONF_TIMER_SWITCH, 0) == 1
        ):
            await self._handle_action(
                {
                    CONF_ATTRS: {
                        CONF_DEROG_MODE: 0,
                        CONF_DEROG_TIME: 0,
                        CONF_TIMER_SWITCH: 0,
                    }
                }
            )

    async def _async_derog_mode_action(self, derog_mode) -> bool:
        """Execute derogation mode."""
        if derog_mode not in [PRESET_BOOST, PRESET_VACATION, PRESET_PRESENCE_DETECT]:
            return False

        if derog_mode == PRESET_BOOST:
            minutes = self._device.get("boost", DEFAULT_BOOST)
            await self._async_boost_mode(int(minutes))
        if derog_mode == PRESET_VACATION:
            days = self._device.get("vacation", DEFAULT_VACATION)
            await self._async_vacation_mode(int(days))
        if derog_mode == PRESET_PRESENCE_DETECT:
            await self._async_presence_detection()

        return True

    async def _async_vacation_mode(self, delay: int) -> None:
        """Service Vacation Mode."""
        await self._async_derog_mode(1, delay)

    async def _async_boost_mode(self, delay: int) -> None:
        """Service Boost Mode."""
        await self._async_derog_mode(2, delay)

    async def _async_presence_detection(self) -> None:
        """Presence detection derog."""
        return await self._async_derog_mode(3)


class HeatzyPiloteV1Thermostat(HeatzyThermostat):
    """Heaty Pilote v1."""

    def __init__(
        self,
        coordinator: HeatzyDataUpdateCoordinator,
        entity_description: HeatzyClimateEntityDescription,
        did: str,
    ) -> None:
        """Init."""
        super().__init__(coordinator, entity_description, did)
        self.async_control_device = coordinator.api.async_control_device

    async def async_turn_auto(self) -> None:
        """Turn device to Program mode."""
        config = {"raw": {CONF_TIMER_SWITCH: 1, CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0}}
        await self._handle_action(config, "Error while turn auto")
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if await self._async_derog_mode_action(preset_mode) is False:
            mode = self.entity_description.ha_to_heatzy_state.get(preset_mode)
            config = {"raw": mode}
            await self._handle_action(config, f"Error preset mode: {preset_mode}")
            await self.coordinator.async_request_refresh()


class HeatzyPiloteV2Thermostat(HeatzyThermostat):
    """Heaty Pilote v2."""


class HeatzyPiloteV3Thermostat(HeatzyPiloteV2Thermostat):
    """Pilote_Soc_C3, Elec_Pro_Ble, Sauter."""


class Glowv1Thermostat(HeatzyPiloteV2Thermostat):
    """Glow."""

    @property
    def current_temperature(self) -> float:
        """Return current temperature."""
        return self._attrs.get(self.entity_description.current_temperature, 0) / 10

    @property
    def target_temperature_high(self) -> float:
        """Return comfort temperature."""
        cft_tempH = self._attrs.get(self.entity_description.temperature_high, 0)
        cft_tempL = self._attrs.get(self.entity_description.temperature_low, 0)

        if self.preset_mode in [PRESET_AWAY, PRESET_VACATION]:
            cft_tempH = 0
            cft_tempL = FROST_TEMP * 10

        return (cft_tempL + (cft_tempH * 256)) / 10

    @property
    def target_temperature_low(self) -> float:
        """Return comfort temperature."""
        eco_tempH = self._attrs.get(self.entity_description.eco_temperature_high, 0)
        eco_tempL = self._attrs.get(self.entity_description.eco_temperature_low, 0)

        if self.preset_mode in [PRESET_AWAY, PRESET_VACATION]:
            eco_tempH = 0
            eco_tempL = FROST_TEMP * 10

        return (eco_tempL + (eco_tempH * 256)) / 10

    @property
    def hvac_action(self) -> HVACAction:
        """Return hvac action ie. heating, off mode."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.target_temperature and (
            self.current_temperature > self.target_temperature
        ):
            return HVACAction.OFF
        return HVACAction.HEATING

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        if self._attrs.get(CONF_ON_OFF) == 0:
            return HVACMode.OFF
        if self._attrs.get(CONF_DEROG_MODE) == 1:
            return HVACMode.AUTO

        return HVACMode.HEAT

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature for mode."""
        # Target temp is set to Low/High/Away value according to the current [preset] mode
        if self.hvac_mode == HVACMode.OFF:
            return None
        if self.preset_mode == PRESET_ECO:
            return self.target_temperature_low
        if self.preset_mode == PRESET_COMFORT:
            return self.target_temperature_high
        if self.preset_mode in [PRESET_AWAY, PRESET_VACATION]:
            return FROST_TEMP

        return None

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        if self._attrs.get(CONF_DEROG_MODE) == 2:
            return PRESET_VACATION

        return self.entity_description.heatzy_to_ha_state.get(
            self._attrs.get(CONF_CUR_MODE)
        )

    async def async_turn_on(self) -> None:
        """Turn device on."""
        config = {CONF_ATTRS: {CONF_ON_OFF: True, CONF_DEROG_MODE: 0}}
        await self._handle_action(config, f"Error to turn on {self.unique_id}")

    async def async_turn_off(self) -> None:
        """Turn device off."""
        config = {CONF_ATTRS: {CONF_ON_OFF: False, CONF_DEROG_MODE: 0}}
        await self._handle_action(config, f"Error to turn on {self.unique_id}")

    async def async_turn_auto(self) -> None:
        """Turn device off."""
        config = {CONF_ATTRS: {CONF_ON_OFF: True, CONF_DEROG_MODE: 1}}
        await self._handle_action(config, f"Error to turn auto {self.unique_id}")

    async def _async_vacation_mode(self, delay: int) -> None:
        """Service Vacation Mode."""
        await self._async_derog_mode(2, delay)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp_eco := kwargs.get(ATTR_TARGET_TEMP_LOW)) and (
            temp_cft := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ):
            config = {
                CONF_ATTRS: {
                    CFT_TEMP_L: int(temp_cft * 10),
                    ECO_TEMP_L: int(temp_eco * 10),
                }
            }

            await self._handle_action(config, "Error to set temperature")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if await self._async_derog_mode_action(preset_mode) is False:
            mode = self.entity_description.ha_to_heatzy_state.get(preset_mode)
            config = {CONF_ATTRS: {CONF_MODE: mode, CONF_ON_OFF: True}}

            if preset_mode == PRESET_AWAY:
                config[CONF_ATTRS].update({CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0})
            elif self.hvac_mode == HVACMode.AUTO:
                config[CONF_ATTRS].update({CONF_DEROG_MODE: 1})
            else:
                config[CONF_ATTRS].update({CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0})
            await self._handle_action(config, f"Error preset mode: {preset_mode}")


class Bloomv1Thermostat(HeatzyPiloteV2Thermostat):
    """Bloom."""

    @property
    def current_temperature(self) -> float:
        """Return current temperature."""
        return self._attrs.get(self.entity_description.current_temperature)

    @property
    def target_temperature_high(self) -> float:
        """Return comfort temperature."""
        return self._attrs.get(self.entity_description.temperature_high)

    @property
    def target_temperature_low(self) -> float:
        """Return echo temperature."""
        return self._attrs.get(self.entity_description.temperature_low)

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature for mode."""
        # Target temp is set to value according to the current [preset] mode
        if self.hvac_mode == HVACMode.OFF:
            return None
        if self.preset_mode == PRESET_ECO:
            return self.target_temperature_low
        if self.preset_mode == PRESET_COMFORT:
            return self.target_temperature_high
        if self.preset_mode == PRESET_AWAY:
            return FROST_TEMP
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp_eco := kwargs.get(ATTR_TARGET_TEMP_LOW)) and (
            temp_cft := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ):
            config = {
                CONF_ATTRS: {CONF_CFT_TEMP: int(temp_cft), CONF_ECO_TEMP: int(temp_eco)}
            }
            await self._handle_action(config, "Error to set temperature")


class HeatzyPiloteProV1(HeatzyPiloteV2Thermostat):
    """Heatzy Pilote Pro."""

    @property
    def current_humidity(self) -> float:
        """Return current humidity."""
        return self._attrs.get(CONF_HUMIDITY)

    @property
    def current_temperature(self) -> float:
        """Return current temperature."""
        return self._attrs.get(self.entity_description.current_temperature, 0) / 10

    @property
    def target_temperature_high(self) -> float:
        """Return comfort temperature."""
        return self._attrs.get(self.entity_description.temperature_high, 0) / 10

    @property
    def target_temperature_low(self) -> float:
        """Return echo temperature."""
        return self._attrs.get(self.entity_description.temperature_low, 0) / 10

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature for mode."""
        if self.hvac_mode == HVACMode.OFF:
            return None
        if self.preset_mode == PRESET_ECO:
            return self.target_temperature_low
        if self.preset_mode == PRESET_COMFORT:
            return self.target_temperature_high
        if self.preset_mode == PRESET_AWAY:
            return FROST_TEMP
        return None

    @property
    def hvac_action(self) -> HVACAction:
        """Return hvac action ie. heating, off mode."""
        if self._attrs.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self._attrs.get(CONF_HEATING_STATE) == 1:
            return HVACAction.OFF
        if self.target_temperature and (
            self.current_temperature > self.target_temperature
        ):
            return HVACAction.OFF
        return HVACAction.HEATING

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp_eco := kwargs.get(ATTR_TARGET_TEMP_LOW)) and (
            temp_cft := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ):
            config = {
                CONF_ATTRS: {
                    CONF_CFT_TEMP: int(temp_cft) * 10,
                    CONF_ECO_TEMP: int(temp_eco) * 10,
                }
            }
            await self._handle_action(config, "Error to set temperature")

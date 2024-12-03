"""Climate sensors for Heatzy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, Final

from heatzypy.exception import HeatzyException
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
    CONF_IS_ONLINE,
    CONF_MODE,
    CONF_ON_OFF,
    CONF_PRODUCT_KEY,
    CONF_TIMER_SWITCH,
    ECO_TEMP_H,
    ECO_TEMP_L,
    FROST_TEMP,
    GLOW,
    PILOTE_PRO_V1,
    PILOTE_V1,
    PILOTE_V2,
    PILOTE_V3,
    PRESET_COMFORT_1,
    PRESET_COMFORT_2,
    PRESET_PRESENCE_DETECT,
    PRESET_VACATION,
)
from .entity import HeatzyEntity

SERVICES = [
    ["boost", {vol.Required(CONF_DELAY): cv.positive_int}, "async_boost_mode"],
    ["vacation", {vol.Required(CONF_DELAY): cv.positive_int}, "async_vacation_mode"],
]


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeatzyClimateEntityDescription(ClimateEntityDescription):
    """Represents an Flow Sensor."""

    fn: Callable[..., Any] | None = None
    products: list[str] | None = None
    stop: int | str | None = None
    heatzy_to_ha_state: dict[int | str, str] | None = None
    ha_to_heatzy_state: dict[int | str, str | int | list[int]] | None = None
    temperature_unit = UnitOfTemperature.CELSIUS
    hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
    preset_modes: list[str] | None = None
    supported_features: tuple[str] | None = None
    target_temperature_step: float | int | None = None
    temperature_high: float | int | None = None
    temperature_low: float | int | None = None
    eco_temperature_high: float | int | None = None
    eco_temperature_low: float | int | None = None
    current_temperature: float | int | None = None


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
        supported_features=(
            ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        ),
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
        stop="\u505c\u6b62",
    ),
    HeatzyClimateEntityDescription(
        key="pilote_v2",
        translation_key="pilote_v2",
        products=PILOTE_V2,
        fn=lambda x, y, z: HeatzyPiloteV2Thermostat(x, y, z),
        preset_modes=[
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_BOOST,
            PRESET_VACATION,
        ],
        supported_features=(
            ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        ),
        heatzy_to_ha_state={
            "cft": PRESET_COMFORT,
            "eco": PRESET_ECO,
            "fro": PRESET_AWAY,
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
        },
        stop="stop",
    ),
    HeatzyClimateEntityDescription(
        key="pilote_v3",
        translation_key="pilote_v3",
        products=PILOTE_V3,
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
        supported_features=(
            ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        ),
        heatzy_to_ha_state={
            "cft": PRESET_COMFORT,
            "eco": PRESET_ECO,
            "fro": PRESET_AWAY,
            "cft1": PRESET_COMFORT_1,
            "cft2": PRESET_COMFORT_2,
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
            PRESET_COMFORT_1: "cft1",
            PRESET_COMFORT_2: "cft2",
        },
        stop="stop",
    ),
    HeatzyClimateEntityDescription(
        key="glow",
        translation_key="glow",
        products=GLOW,
        fn=lambda x, y, z: Glowv1Thermostat(x, y, z),
        preset_modes=[
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_BOOST,
            PRESET_VACATION,
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
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
        },
        stop="stop",
        temperature_high=CFT_TEMP_H,
        temperature_low=CFT_TEMP_L,
        eco_temperature_high=ECO_TEMP_H,
        eco_temperature_low=ECO_TEMP_L,
        target_temperature_step=1,
    ),
    HeatzyClimateEntityDescription(
        key="bloom",
        translation_key="bloom",
        products=BLOOM,
        fn=lambda x, y, z: Bloomv1Thermostat(x, y, z),
        preset_modes=[
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_BOOST,
            PRESET_VACATION,
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
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
            PRESET_COMFORT_1: "cft1",
            PRESET_COMFORT_2: "cft2",
        },
        stop="stop",
        current_temperature=CONF_CUR_TEMP,
        temperature_high=CONF_CFT_TEMP,
        temperature_low=CONF_ECO_TEMP,
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
        },
        ha_to_heatzy_state={
            PRESET_COMFORT: "cft",
            PRESET_ECO: "eco",
            PRESET_AWAY: "fro",
            PRESET_COMFORT_1: "cft1",
            PRESET_COMFORT_2: "cft2",
        },
        stop="stop",
        current_temperature=CONF_CUR_TEMP,
        temperature_high=CONF_CFT_TEMP,
        temperature_low=CONF_ECO_TEMP,
        target_temperature_step=1,
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
        self._attr_temperature_unit = entity_description.temperature_unit
        self._attr_supported_features = entity_description.supported_features
        self._attr_preset_modes = entity_description.preset_modes
        self._attr_hvac_modes = entity_description.hvac_modes
        self._attr_available = coordinator.data[did].get(CONF_IS_ONLINE, True)

    @property
    def hvac_action(self) -> HVACAction:
        """Return hvac action ie. heat, cool mode."""
        mode = self._attrs.get(CONF_MODE)
        return (
            HVACAction.OFF
            if mode == self.entity_description.stop
            else HVACAction.HEATING
        )

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        if self._attrs.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO

        # If preset mode is NONE set HVAC Mode to OFF
        if self._attrs.get(CONF_MODE) == self.entity_description.stop:
            return HVACMode.OFF
        # otherwise set HVAC Mode to HEAT
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
        await self.async_set_preset_mode(PRESET_COMFORT)

    async def async_turn_off(self) -> None:
        """Turn device off."""
        await self.async_set_preset_mode(PRESET_NONE)

    async def async_turn_auto(self) -> None:
        """Presence detection derog."""
        raise NotImplementedError

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        elif hvac_mode == HVACMode.AUTO:
            await self.async_turn_auto()
        elif hvac_mode == HVACMode.HEAT:
            await self.async_turn_on()

    async def async_vacation_mode(self, delay: int) -> None:
        """Vacation derog."""
        raise NotImplementedError

    async def async_boost_mode(self, delay: int) -> None:
        """Boost derog."""
        raise NotImplementedError

    async def async_presence_detection(self) -> None:
        """Presence detection derog."""
        raise NotImplementedError

    # @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attrs = self.coordinator.data.get(self.unique_id, {}).get(CONF_ATTRS, {})
        self._attr_available = self.coordinator.data.get(self.unique_id, {}).get(
            CONF_IS_ONLINE, True
        )
        self.async_write_ha_state()


class HeatzyPiloteV1Thermostat(HeatzyThermostat):
    """Heaty Pilote v1."""

    async def async_turn_auto(self) -> None:
        """Turn device to Program mode."""
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id,
                {
                    "raw": {
                        CONF_TIMER_SWITCH: 1,
                        CONF_DEROG_MODE: 0,
                        CONF_DEROG_TIME: 0,
                    }
                },
            )
            await self.coordinator.async_request_refresh()

        except HeatzyException as error:
            _LOGGER.error("Error while turn auto (%s)", error)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_BOOST:
            return await self.async_boost_mode(60)  # minutes
        if preset_mode == PRESET_VACATION:
            return await self.async_vacation_mode(60)  # days

        try:
            await self.coordinator.api.async_control_device(
                self.unique_id,
                {"raw": self.entity_description.ha_to_heatzy_state[preset_mode]},
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Error while preset mode: %s (%s)", preset_mode, error)

    async def async_derog_mode(self, mode: int, delay: int) -> None:
        """Derogation mode."""
        config: dict[str, Any] = {
            CONF_ATTRS: {CONF_DEROG_TIME: delay, CONF_DEROG_MODE: mode}
        }
        if mode == 1:
            config[CONF_ATTRS][CONF_MODE] = self.entity_description.ha_to_heatzy_state[
                PRESET_AWAY
            ]
        if mode == 2:
            config[CONF_ATTRS][CONF_MODE] = self.entity_description.ha_to_heatzy_state[
                PRESET_COMFORT
            ]

        try:
            await self.coordinator.api.async_control_device(self.unique_id, config)
        except HeatzyException as error:
            _LOGGER.error("Error to set derog mode: %s (%s)", mode, error)


class HeatzyPiloteV2Thermostat(HeatzyThermostat):
    """Heaty Pilote v2."""

    async def async_turn_on(self) -> None:
        """Turn device on."""
        try:
            if (
                self._attrs.get(CONF_DEROG_MODE) > 0
                or self._attrs.get(CONF_TIMER_SWITCH) == 1
            ):
                await self.coordinator.api.websocket.async_control_device(
                    self.unique_id,
                    {
                        CONF_ATTRS: {
                            CONF_DEROG_MODE: 0,
                            CONF_DEROG_TIME: 0,
                            CONF_TIMER_SWITCH: 0,
                        }
                    },
                )

            await self.coordinator.api.websocket.async_control_device(
                self.unique_id,
                {
                    CONF_ATTRS: {
                        CONF_MODE: self.entity_description.ha_to_heatzy_state[
                            PRESET_COMFORT
                        ]
                    }
                },
            )
        except HeatzyException as error:
            _LOGGER.error("Error to turn on (%s)", error)

    async def async_turn_off(self) -> None:
        """Turn device on."""
        try:
            if (
                self._attrs.get(CONF_DEROG_MODE) > 0
                or self._attrs.get(CONF_TIMER_SWITCH) == 1
            ):
                await self.coordinator.api.websocket.async_control_device(
                    self.unique_id,
                    {
                        CONF_ATTRS: {
                            CONF_DEROG_MODE: 0,
                            CONF_DEROG_TIME: 0,
                            CONF_TIMER_SWITCH: 0,
                        }
                    },
                )

            await self.coordinator.api.websocket.async_control_device(
                self.unique_id,
                {CONF_ATTRS: {CONF_MODE: self.entity_description.stop}},
            )
        except HeatzyException as error:
            _LOGGER.error("Error to turn off (%s)", error)

    async def async_turn_auto(self) -> None:
        """Turn device to Program mode."""
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id,
                {
                    CONF_ATTRS: {
                        CONF_TIMER_SWITCH: 1,
                        CONF_DEROG_MODE: 0,
                        CONF_DEROG_TIME: 0,
                    }
                },
            )
        except HeatzyException as error:
            _LOGGER.error("Error to turn auto (%s)", error)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_BOOST:
            return await self.async_boost_mode(60)  # minutes
        if preset_mode == PRESET_VACATION:
            return await self.async_vacation_mode(60)  # days

        config: dict[str, Any] = {
            CONF_ATTRS: {
                CONF_MODE: self.entity_description.ha_to_heatzy_state[preset_mode]
            }
        }
        # If in VACATION mode then as well as setting preset mode we also stop the VACATION mode
        if self._attrs.get(CONF_DEROG_MODE) > 0:
            config[CONF_ATTRS].update({CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0})

        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, config
            )
        except HeatzyException as error:
            _LOGGER.error("Error to set preset mode: %s (%s)", preset_mode, error)

    async def async_vacation_mode(self, delay: int) -> None:
        """Service Vacation Mode."""
        await self.async_derog_mode(1, delay)

    async def async_boost_mode(self, delay: int) -> None:
        """Service Boost Mode."""
        await self.async_derog_mode(2, delay)

    async def async_derog_mode(self, mode: int, delay: int | None = None) -> None:
        """Derogation mode."""
        config: dict[str, Any] = {CONF_ATTRS: {CONF_DEROG_MODE: mode}}
        if mode == 1:
            config[CONF_ATTRS][CONF_MODE] = self.entity_description.ha_to_heatzy_state[
                PRESET_AWAY
            ]
            config[CONF_ATTRS][CONF_DEROG_TIME] = delay

        if mode == 2:
            config[CONF_ATTRS][CONF_MODE] = self.entity_description.ha_to_heatzy_state[
                PRESET_COMFORT
            ]
            config[CONF_ATTRS][CONF_DEROG_TIME] = delay

        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, config
            )
        except HeatzyException as error:
            _LOGGER.error("Error to set derog mode: %s (%s)", mode, error)


class HeatzyPiloteV3Thermostat(HeatzyPiloteV2Thermostat):
    """Pilote_Soc_C3, Elec_Pro_Ble, Sauter."""


class Glowv1Thermostat(HeatzyPiloteV2Thermostat):
    """Glow."""

    @property
    def current_temperature(self) -> float:
        """Return current temperature."""
        cur_tempH = self._attrs.get(self.entity_description.temperature_high, 0)
        cur_tempL = self._attrs.get(self.entity_description.temperature_low, 0)
        return (cur_tempL + (cur_tempH * 256)) / 10

    @property
    def target_temperature_high(self) -> float:
        """Return comfort temperature."""
        cft_tempL = self._attrs.get(self.entity_description.temperature_high, 0)
        cft_tempH = self._attrs.get(self.entity_description.temperature_low, 0)

        return (cft_tempL + (cft_tempH * 256)) / 10

    @property
    def target_temperature_low(self) -> float:
        """Return comfort temperature."""
        eco_tempH = self._attrs.get(self.entity_description.eco_temperature_high, 0)
        eco_tempL = self._attrs.get(self.entity_description.eco_temperature_low, 0)
        return (eco_tempL + (eco_tempH * 256)) / 10

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        if self._attrs.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO

        if self._attrs.get(CONF_ON_OFF) == 0:
            return HVACMode.OFF
        # Otherwise set HVAC Mode to HEAT
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
        if self.preset_mode == PRESET_AWAY:
            return FROST_TEMP
        return None

    @property
    def hvac_action(self) -> HVACAction:
        """Return hvac action ie. heat, cool mode."""
        if self._attrs.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        # If Target temp is higher than current temp then set HVAC Action to HEATING
        if self.target_temperature and (
            self.current_temperature < self.target_temperature
        ):
            return HVACAction.HEATING
        # Otherwise set to IDLE
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        mode = self._attrs.get(CONF_CUR_MODE)
        return (
            PRESET_AWAY
            if self._attrs.get(CONF_ON_OFF) == 0
            and self._attrs.get(CONF_DEROG_MODE) == 2
            else self.entity_description.heatzy_to_ha_state.get(mode)
        )

    async def async_turn_on(self) -> None:
        """Turn device on."""
        # When turning ON ensure PROGRAM and VACATION mode are OFF
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_ON_OFF: True, CONF_DEROG_MODE: 0}}
            )
        except HeatzyException as error:
            _LOGGER.error("Error to turn on : %s", error)

    async def async_turn_off(self) -> None:
        """Turn device off."""
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_ON_OFF: False, CONF_DEROG_MODE: 0}}
            )
        except HeatzyException as error:
            _LOGGER.error("Error to turn off : %s", error)

    async def async_turn_auto(self) -> None:
        """Turn device off."""
        # When setting to PROGRAM Mode we also ensure it's turned ON
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_ON_OFF: True, CONF_DEROG_MODE: 1}}
            )
        except HeatzyException as error:
            _LOGGER.error("Error to turn auto : %s", error)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temp_h = self.entity_description.temperature_high
        temp_l = self.entity_description.temperature_low
        eco_temp_h = self.entity_description.eco_temperature_high
        eco_temp_l = self.entity_description.eco_temperature_low

        if (temp_eco := kwargs.get(ATTR_TARGET_TEMP_LOW)) and (
            temp_cft := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ):
            self._attrs[eco_temp_l] = int(temp_eco * 10)
            self._attrs[temp_l] = int(temp_cft * 10)

            try:
                await self.coordinator.api.websocket.async_control_device(
                    self.unique_id,
                    {
                        CONF_ATTRS: {
                            CFT_TEMP_L: self._attrs[temp_h],
                            ECO_TEMP_L: self._attrs[eco_temp_h],
                        }
                    },
                )
            except HeatzyException as error:
                _LOGGER.error("Error to set temperature (%s)", error)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_BOOST:
            return await self.async_boost_mode(60)  # minutes
        if preset_mode == PRESET_VACATION:
            return await self.async_vacation_mode(60)  # days

        config = {
            CONF_ATTRS: {
                CONF_MODE: self.entity_description.ha_to_heatzy_state[preset_mode],
                CONF_ON_OFF: True,
            }
        }
        # If in VACATION mode then as well as setting preset mode we also stop the VACATION mode
        if self._attrs.get(CONF_DEROG_MODE) == 2:
            config[CONF_ATTRS].update({CONF_DEROG_MODE: 0})
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, config
            )
        except HeatzyException as error:
            _LOGGER.error("Error to set preset mode: %s (%s)", preset_mode, error)


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

    @property
    def hvac_action(self) -> HVACAction:
        """Return hvac action ie. heat, cool mode."""
        if self._attrs.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        # If Target temp is higher than current temp then set HVAC Action to HEATING
        if self.target_temperature and (
            self.current_temperature < self.target_temperature
        ):
            return HVACAction.HEATING
        # Otherwise set to IDLE
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp_eco := kwargs.get(ATTR_TARGET_TEMP_LOW)) and (
            temp_cft := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ):
            self._attrs[CONF_ECO_TEMP] = int(temp_eco)
            self._attrs[CONF_CFT_TEMP] = int(temp_cft)

            try:
                await self.coordinator.api.websocket.async_control_device(
                    self.unique_id,
                    {
                        CONF_ATTRS: {
                            CONF_CFT_TEMP: self._attrs[CONF_CFT_TEMP],
                            CONF_ECO_TEMP: self._attrs[CONF_ECO_TEMP],
                        }
                    },
                )
            except HeatzyException as error:
                _LOGGER.error("Error to set temperature (%s)", error)


class HeatzyPiloteProV1(HeatzyPiloteV3Thermostat):
    """Heatzy Pilote Pro."""

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
        """Return hvac action ie. heat, cool mode."""
        if self._attrs.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        # if Target tem is reached
        if self._attrs.get(CONF_HEATING_STATE) == 1:
            return HVACAction.IDLE
        # If Target temp is higher than current temp then set HVAC Action to HEATING
        if self.target_temperature and (
            self.current_temperature < self.target_temperature
        ):
            return HVACAction.HEATING
        # Otherwise set to IDLE
        return HVACAction.IDLE

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_BOOST:
            return await self.async_boost_mode(60)  # minutes
        if preset_mode == PRESET_VACATION:
            return await self.async_vacation_mode(60)  # days
        if preset_mode == PRESET_PRESENCE_DETECT:
            return await self.async_presence_detection()  # days

        config: dict[str, Any] = {
            CONF_ATTRS: {
                CONF_MODE: self.entity_description.ha_to_heatzy_state[preset_mode]
            }
        }
        if self._attrs.get(CONF_DEROG_MODE) > 0:
            config[CONF_ATTRS].update({CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0})

        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, config
            )
        except HeatzyException as error:
            _LOGGER.error("Error to set preset mode: %s (%s)", preset_mode, error)

    async def async_presence_detection(self) -> None:
        """Service Window Detection Mode."""
        await self.async_derog_mode(3)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp_eco := kwargs.get(ATTR_TARGET_TEMP_LOW)) and (
            temp_cft := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ):
            self._attrs[CONF_ECO_TEMP] = int(temp_eco) * 10
            self._attrs[CONF_CFT_TEMP] = int(temp_cft) * 10

            try:
                await self.coordinator.api.websocket.async_control_device(
                    self.unique_id,
                    {
                        CONF_ATTRS: {
                            CONF_CFT_TEMP: self._attrs[CONF_CFT_TEMP],
                            CONF_ECO_TEMP: self._attrs[CONF_ECO_TEMP],
                        }
                    },
                )
            except HeatzyException as error:
                _LOGGER.error("Error to set temperature (%s)", error)

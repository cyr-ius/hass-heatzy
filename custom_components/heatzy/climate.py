"""Climate sensors for Heatzy."""

from __future__ import annotations

import logging
from typing import Any

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
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import CONF_DELAY, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HeatzyConfigEntry, HeatzyDataUpdateCoordinator
from .const import (
    BLOOM,
    CFT_TEMP_H,
    CFT_TEMP_L,
    CONF_ALIAS,
    CONF_ATTRS,
    CONF_CFT_TEMP,
    CONF_CUR_MODE,
    CONF_CUR_TEMP,
    CONF_DEROG_MODE,
    CONF_DEROG_TIME,
    CONF_ECO_TEMP,
    CONF_IS_ONLINE,
    CONF_MODE,
    CONF_MODEL,
    CONF_ON_OFF,
    CONF_PRODUCT_KEY,
    CONF_TIMER_SWITCH,
    CONF_VERSION,
    CUR_TEMP_H,
    CUR_TEMP_L,
    DOMAIN,
    ECO_TEMP_H,
    ECO_TEMP_L,
    FROST_TEMP,
    GLOW,
    PILOTE_V1,
    PILOTE_V2,
    PRESET_COMFORT_1,
    PRESET_COMFORT_2,
    SAUTER,
)

SERVICES = [
    ["boost", {vol.Required(CONF_DELAY): cv.positive_int}, "async_boost_mode"],
    ["vacation", {vol.Required(CONF_DELAY): cv.positive_int}, "async_vacation_mode"],
]

_LOGGER = logging.getLogger(__name__)


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
        if product_key in PILOTE_V1:
            entities.append(HeatzyPiloteV1Thermostat(coordinator, unique_id))
        elif product_key in PILOTE_V2:
            entities.append(HeatzyPiloteV2Thermostat(coordinator, unique_id))
        elif product_key in GLOW:
            entities.append(Glowv1Thermostat(coordinator, unique_id))
        elif product_key in BLOOM:
            entities.append(Bloomv1Thermostat(coordinator, unique_id))
        elif product_key in SAUTER:
            entities.append(SauterThermostat(coordinator, unique_id))
    async_add_entities(entities)


class HeatzyThermostat(CoordinatorEntity[HeatzyDataUpdateCoordinator], ClimateEntity):
    """Heatzy climate."""

    HEATZY_STOP: int | str | None = None
    HEATZY_TO_HA_STATE: dict[int | str, str] = {}
    HA_TO_HEATZY_STATE: dict[int | str, str | int | list[int]] = {}

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]
    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = True
    _attr_name = None
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self, coordinator: HeatzyDataUpdateCoordinator, unique_id: str
    ) -> None:
        """Init."""
        super().__init__(coordinator, context=unique_id)
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer=DOMAIN.capitalize(),
            sw_version=coordinator.data[unique_id].get(CONF_VERSION),
            model=coordinator.data[unique_id].get(CONF_MODEL),
            name=coordinator.data[unique_id][CONF_ALIAS],
        )
        self._attr = coordinator.data[unique_id].get(CONF_ATTRS, {})
        self._attr_available = coordinator.data[unique_id].get(CONF_IS_ONLINE, True)

    @property
    def hvac_action(self) -> HVACAction:
        """Return hvac action ie. heat, cool mode."""
        return (
            HVACAction.OFF
            if self._attr.get(CONF_MODE) == self.HEATZY_STOP
            else HVACAction.HEATING
        )

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        # If TIMER_SWTICH = 1 then set HVAC Mode to AUTO
        if self._attr.get(CONF_TIMER_SWITCH) == 1:
            return HVACMode.AUTO
        # If preset mode is NONE set HVAC Mode to OFF
        if self._attr.get(CONF_MODE) == self.HEATZY_STOP:
            return HVACMode.OFF
        # otherwise set HVAC Mode to HEAT
        return HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        return self.HEATZY_TO_HA_STATE.get(self._attr.get(CONF_MODE))

    async def async_turn_on(self) -> None:
        """Turn device on."""
        await self.async_set_preset_mode(PRESET_COMFORT)

    async def async_turn_off(self) -> None:
        """Turn device off."""
        await self.async_set_preset_mode(PRESET_NONE)

    async def async_turn_auto(self) -> None:
        """Turn device to Program mode."""
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
        """Service Vacation Mode."""
        raise NotImplementedError

    async def async_boost_mode(self, delay: int) -> None:
        """Service Boost Mode."""
        raise NotImplementedError

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr = self.coordinator.data[self.unique_id].get(CONF_ATTRS, {})
        self._attr_available = self.coordinator.data[self.unique_id].get(
            CONF_IS_ONLINE, True
        )
        self.async_write_ha_state()


class HeatzyPiloteV1Thermostat(HeatzyThermostat):
    """Heaty Pilote v1."""

    HEATZY_TO_HA_STATE = {
        "\u8212\u9002": PRESET_COMFORT,
        "\u7ecf\u6d4e": PRESET_ECO,
        "\u89e3\u51bb": PRESET_AWAY,
        "\u505c\u6b62": PRESET_NONE,
    }
    HA_TO_HEATZY_STATE = {
        PRESET_COMFORT: [1, 1, 0],
        PRESET_ECO: [1, 1, 1],
        PRESET_AWAY: [1, 1, 2],
        PRESET_NONE: [1, 1, 3],
    }

    HEATZY_STOP = "\u505c\u6b62"

    async def async_turn_auto(self) -> None:
        """Turn device to Program mode."""
        # For PROGRAM Mode we have to set TIMER_SWITCH = 1, but we also ensure VACATION Mode is OFF
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
        except HeatzyException as error:
            _LOGGER.error("Error while turn off (%s)", error)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id,
                {"raw": self.HA_TO_HEATZY_STATE.get(preset_mode)},
            )

        except HeatzyException as error:
            _LOGGER.error("Error while preset mode: %s (%s)", preset_mode, error)


class HeatzyPiloteV2Thermostat(HeatzyThermostat):
    """Heaty Pilote v2."""

    # TIMER_SWITCH = 1 is PROGRAM Mode
    # DEROG_MODE = 1 is VACATION Mode
    # DEROG_MODE = 2 is BOOST Mode
    HEATZY_TO_HA_STATE = {"cft": PRESET_COMFORT, "eco": PRESET_ECO, "fro": PRESET_AWAY}
    HA_TO_HEATZY_STATE = {PRESET_COMFORT: "cft", PRESET_ECO: "eco", PRESET_AWAY: "fro"}
    HEATZY_STOP = "stop"
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY, PRESET_BOOST]

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        return (
            PRESET_BOOST
            if self._attr.get(CONF_DEROG_MODE) == 2
            else self.HEATZY_TO_HA_STATE.get(self._attr.get(CONF_MODE))
        )

    async def async_turn_on(self) -> None:
        """Turn device on."""
        try:
            if (
                self._attr.get(CONF_DEROG_MODE) > 0
                or self._attr.get(CONF_TIMER_SWITCH) == 1
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
                {CONF_ATTRS: {CONF_MODE: self.HA_TO_HEATZY_STATE[PRESET_COMFORT]}},
            )
        except HeatzyException as error:
            _LOGGER.error("Error to turn on (%s)", error)

    async def async_turn_off(self) -> None:
        """Turn device on."""
        try:
            if (
                self._attr.get(CONF_DEROG_MODE) > 0
                or self._attr.get(CONF_TIMER_SWITCH) == 1
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
                {CONF_ATTRS: {CONF_MODE: self.HEATZY_STOP}},
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
            return await self.async_boost_mode(60)

        config: dict[str, Any] = {
            CONF_ATTRS: {CONF_MODE: self.HA_TO_HEATZY_STATE.get(preset_mode)}
        }
        # If in VACATION mode then as well as setting preset mode we also stop the VACATION mode
        if self._attr.get(CONF_DEROG_MODE) > 0:
            config[CONF_ATTRS].update({CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0})
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, config
            )
        except HeatzyException as error:
            _LOGGER.error("Error to set preset mode: %s (%s)", preset_mode, error)

    async def async_vacation_mode(self, delay: int) -> None:
        """Service Vacation Mode."""
        await self._async_derog_mode(1, delay)

    async def async_boost_mode(self, delay: int) -> None:
        """Service Boost Mode."""
        await self._async_derog_mode(2, delay)

    async def _async_derog_mode(self, mode: int, delay: int) -> None:
        """Derog for boost and vacation mode."""
        config: dict[str, Any] = {
            CONF_ATTRS: {CONF_DEROG_TIME: delay, CONF_DEROG_MODE: mode}
        }
        if mode == 2:
            config[CONF_ATTRS][CONF_MODE] = self.HA_TO_HEATZY_STATE.get(PRESET_COMFORT)

        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, config
            )
        except HeatzyException as error:
            _LOGGER.error("Error to set derog mode: %s (%s)", mode, error)


class Glowv1Thermostat(HeatzyPiloteV2Thermostat):
    """Glow."""

    # DEROG_MODE = 1 is PROGRAM Mode
    # DEROG_MODE = 2 is VACATION Mode
    HEATZY_TO_HA_STATE = {0: PRESET_COMFORT, 1: PRESET_ECO, 2: PRESET_AWAY}
    HA_TO_HEATZY_STATE = {PRESET_COMFORT: "cft", PRESET_ECO: "eco", PRESET_AWAY: "fro"}
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]
    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    @property
    def current_temperature(self) -> float:
        """Return current temperature."""
        cur_tempH = self._attr.get(CUR_TEMP_H, 0)
        cur_tempL = self._attr.get(CUR_TEMP_L, 0)
        return (cur_tempL + (cur_tempH * 256)) / 10

    @property
    def target_temperature_high(self) -> float:
        """Return comfort temperature."""
        cft_tempH = self._attr.get(CFT_TEMP_H, 0)
        cft_tempL = self._attr.get(CFT_TEMP_L, 0)
        return (cft_tempL + (cft_tempH * 256)) / 10

    @property
    def target_temperature_low(self) -> float:
        """Return comfort temperature."""
        eco_tempH = self._attr.get(ECO_TEMP_H, 0)
        eco_tempL = self._attr.get(ECO_TEMP_L, 0)
        return (eco_tempL + (eco_tempH * 256)) / 10

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        # If OFF...
        if self._attr.get(CONF_ON_OFF) == 0:
            # but in VACATION mode then set HVAC Mode to HEAT
            if self._attr.get(CONF_DEROG_MODE) == 2:
                return HVACMode.HEAT
            # otherwise  set HVAC Mode to OFF
            return HVACMode.OFF
        # Otherwise if in PROGRAM mode set HVAC Mode to AUTO
        if self._attr.get(CONF_DEROG_MODE) == 1:
            return HVACMode.AUTO
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
        # If OFF then set HVAC Action to OFF
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        # If Target temp is higher than current temp then set HVAC Action to HEATING
        if self.target_temperature and (
            self.target_temperature > self.current_temperature
        ):
            return HVACAction.HEATING
        # Otherwise set to IDLE
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., home, away, temp."""
        return (
            PRESET_AWAY
            if self._attr.get(CONF_ON_OFF) == 0 and self._attr.get(CONF_DEROG_MODE) == 2
            else self.HEATZY_TO_HA_STATE.get(self._attr.get(CONF_CUR_MODE))
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
        if (temp_eco := kwargs.get(ATTR_TARGET_TEMP_LOW)) and (
            temp_cft := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ):
            self._attr[ECO_TEMP_L] = int(temp_eco * 10)
            self._attr[CFT_TEMP_L] = int(temp_cft * 10)

            try:
                await self.coordinator.api.websocket.async_control_device(
                    self.unique_id,
                    {
                        CONF_ATTRS: {
                            CFT_TEMP_L: self._attr[CFT_TEMP_L],
                            ECO_TEMP_L: self._attr[ECO_TEMP_L],
                        }
                    },
                )
            except HeatzyException as error:
                _LOGGER.error("Error to set temperature (%s)", error)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        config = {
            CONF_ATTRS: {
                CONF_MODE: self.HA_TO_HEATZY_STATE.get(preset_mode),
                CONF_ON_OFF: True,
            }
        }
        # If in VACATION mode then as well as setting preset mode we also stop the VACATION mode
        if self._attr.get(CONF_DEROG_MODE) == 2:
            config[CONF_ATTRS].update({CONF_DEROG_MODE: 0})
        try:
            await self.coordinator.api.websocket.async_control_device(
                self.unique_id, config
            )
        except HeatzyException as error:
            _LOGGER.error("Error to set preset mode: %s (%s)", preset_mode, error)


class Bloomv1Thermostat(HeatzyPiloteV2Thermostat):
    """Bloom."""

    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]
    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 1

    @property
    def current_temperature(self) -> float:
        """Return current temperature."""
        return self._attr.get(CONF_CUR_TEMP)

    @property
    def target_temperature_high(self) -> float:
        """Return comfort temperature."""
        return self._attr.get(CONF_CFT_TEMP)

    @property
    def target_temperature_low(self) -> float:
        """Return echo temperature."""
        return self._attr.get(CONF_ECO_TEMP)

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
        # If OFF then set HVAC Action to OFF
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        # If Target temp is higher than current temp then set HVAC Action to HEATING
        if self.target_temperature and (
            self.target_temperature > self.current_temperature
        ):
            return HVACAction.HEATING
        # Otherwise set to IDLE
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp_eco := kwargs.get(ATTR_TARGET_TEMP_LOW)) and (
            temp_cft := kwargs.get(ATTR_TARGET_TEMP_HIGH)
        ):
            self._attr[CONF_ECO_TEMP] = int(temp_eco)
            self._attr[CONF_CFT_TEMP] = int(temp_cft)

            try:
                await self.coordinator.api.websocket.async_control_device(
                    self.unique_id,
                    {
                        CONF_ATTRS: {
                            CONF_CFT_TEMP: self._attr[CONF_CFT_TEMP],
                            CONF_ECO_TEMP: self._attr[CONF_ECO_TEMP],
                        }
                    },
                )
            except HeatzyException as error:
                _LOGGER.error("Error to set temperature (%s)", error)


class SauterThermostat(HeatzyPiloteV2Thermostat):
    """Sauter."""

    _attr_preset_modes = [
        PRESET_COMFORT,
        PRESET_ECO,
        PRESET_AWAY,
        PRESET_COMFORT_1,
        PRESET_COMFORT_2,
    ]

    HEATZY_TO_HA_STATE = {
        "cft": PRESET_COMFORT,
        "eco": PRESET_ECO,
        "fro": PRESET_AWAY,
        "cft1": PRESET_COMFORT_1,
        "cft2": PRESET_COMFORT_2,
    }
    HA_TO_HEATZY_STATE = {
        PRESET_COMFORT: "cft",
        PRESET_ECO: "eco",
        PRESET_AWAY: "fro",
        PRESET_COMFORT_1: "cft1",
        PRESET_COMFORT_2: "cft2",
    }

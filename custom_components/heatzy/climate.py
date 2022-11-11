"""Climate sensors for Heatzy."""
import logging
import time

from heatzypy.exception import HeatzyException
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HeatzyDataUpdateCoordinator
from .const import (
    CFT_TEMP_H,
    CFT_TEMP_L,
    CONF_ALIAS,
    CONF_ATTR,
    CONF_MODE,
    CONF_MODEL,
    CONF_ON_OFF,
    CONF_TIMER_SWITCH,
    CONF_DEROG_MODE,
    CONF_DEROG_TIME,
    CONF_CUR_MODE,
    CONF_PRODUCT_KEY,
    CONF_VERSION,
    CUR_TEMP_H,
    CUR_TEMP_L,
    FROST_TEMP,
    DOMAIN,
    ECO_TEMP_H,
    ECO_TEMP_L,
    ELEC_PRO_SOC,
    GLOW,
    PILOTEV1,
    PILOTEV2,
    CONF_ATTRS,
)

MODE_LIST = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
PRESET_LIST = [PRESET_NONE, PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Load all Heatzy devices."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for unique_id, device in coordinator.data.items():
        product_key = device.get(CONF_PRODUCT_KEY)
        if product_key in PILOTEV1:
            entities.append(HeatzyPiloteV1Thermostat(coordinator, unique_id))
        elif product_key in PILOTEV2 or product_key in ELEC_PRO_SOC:
            entities.append(HeatzyPiloteV2Thermostat(coordinator, unique_id))
        elif product_key in GLOW:
            entities.append(Glowv1Thermostat(coordinator, unique_id))
    async_add_entities(entities)


class HeatzyThermostat(CoordinatorEntity[HeatzyDataUpdateCoordinator], ClimateEntity):
    """Heatzy climate."""

    _attr_hvac_modes = MODE_LIST
    _attr_preset_modes = PRESET_LIST
    _attr_supported_features = ClimateEntityFeature.PRESET_MODE
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_has_entity_name = True

    def __init__(self, coordinator: HeatzyDataUpdateCoordinator, unique_id):
        """Init."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = coordinator.data[unique_id][CONF_ALIAS]

    @property
    def device_info(self):
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            manufacturer=DOMAIN,
            sw_version=self.coordinator.data[self.unique_id].get(CONF_VERSION),
            model=self.coordinator.data[self.unique_id].get(CONF_MODEL),
        )

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        if self.preset_mode == PRESET_NONE:
            return HVACMode.OFF
        return HVACMode.HEAT

    async def async_set_hvac_mode(self, hvac_mode: str) -> bool:
        """Set new hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        elif hvac_mode == HVACMode.HEAT:
            await self.async_turn_on()

    async def async_turn_on(self) -> str:
        """Turn device on."""
        await self.async_set_preset_mode(PRESET_COMFORT)

    async def async_turn_off(self) -> str:
        """Turn device off."""
        await self.async_set_preset_mode(PRESET_NONE)


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

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode, e.g., home, away, temp."""
        return self.HEATZY_TO_HA_STATE.get(
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_MODE)
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id,
                {"raw": self.HA_TO_HEATZY_STATE.get(preset_mode)},
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Set preset mode (%s) %s (%s)", preset_mode, error, self.name)


class HeatzyPiloteV2Thermostat(HeatzyThermostat):
    """Heaty Pilote v2."""
    #TIMER_SWITCH = 1 is PROGRAM Mode
    #DEROG_MODE = 1 is VACATION Mode

    # spell-checker:disable
    HEATZY_TO_HA_STATE = {
        "cft": PRESET_COMFORT,
        "eco": PRESET_ECO,
        "fro": PRESET_AWAY,
        "stop": PRESET_NONE,
    }

    HA_TO_HEATZY_STATE = {
        PRESET_COMFORT: "cft",
        PRESET_ECO: "eco",
        PRESET_AWAY: "fro",
        PRESET_NONE: "stop",
    }
    # spell-checker:enable

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode, e.g., home, away, temp."""
        return self.HEATZY_TO_HA_STATE.get(
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_MODE)
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        try:
            #First ensure VACATION mode is disabled (have to do this separately to changing preset mode)
            #But also, if Preset Mode is PRESET_NONE ensure PROGRAM Mode is OFF
            if preset_mode == PRESET_NONE:
                await self.coordinator.api.async_control_device(
                    self.unique_id,
                    {CONF_ATTRS: {CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0, CONF_TIMER_SWITCH: 0}},
                )
            else:
                await self.coordinator.api.async_control_device(
                    self.unique_id,
                    {CONF_ATTRS: {CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0}},
                )
            #Now can set the preset (after 2 seconds)
            time.sleep(2)
            await self.coordinator.api.async_control_device(
                self.unique_id,
                {CONF_ATTRS: {CONF_MODE: self.HA_TO_HEATZY_STATE.get(preset_mode)}},
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Set preset mode (%s) %s (%s)", preset_mode, error, self.name)

    async def async_turn_on(self) -> str:
        """Turn device on."""
        try:
            #First ensure VACATION and PROGRAM mode are disabled (have to do this separately to changing preset mode)
            await self.coordinator.api.async_control_device(
                self.unique_id,
                {CONF_ATTRS: {CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0, CONF_TIMER_SWITCH: 0}},
            )
            #Now can set the preset (after 2 seconds)
            time.sleep(2)
            await self.coordinator.api.async_control_device(
                self.unique_id,
                {CONF_ATTRS: {CONF_MODE: self.HA_TO_HEATZY_STATE.get(PRESET_COMFORT,0)}},
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Set preset mode (%s) %s (%s)", preset_mode, error, self.name)

    async def async_turn_auto(self) -> str:
        """Turn device to Program mode."""
        #For PROGRAM Mode we have to set TIMER_SWITCH = 1, but we also ensure VACATION Mode is OFF
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_TIMER_SWITCH: 1, CONF_DEROG_MODE: 0, CONF_DEROG_TIME: 0}}
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Error to turn off : %s", error)

    @property
    def hvac_mode(self):        
        """Return hvac operation ie. heat, cool mode."""
        #If TIMER_SWTICH = 1 then set HVAC Mode to AUTO
        if (
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_TIMER_SWITCH) == 1
        ):
            return HVACMode.AUTO
        #If preset mode is NONE set HVAC Mode to OFF
        elif self.preset_mode == PRESET_NONE:
            return HVACMode.OFF
        #otherwise set HVAC Mode to HEAT
        return HVACMode.HEAT
   
    async def async_set_hvac_mode(self, hvac_mode: str) -> bool:
        """Set new hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        elif hvac_mode == HVACMode.AUTO:
            await self.async_turn_auto()
        elif hvac_mode == HVACMode.HEAT:
            await self.async_turn_on()

    @property
    def hvac_action(self):
        """Return hvac action ie. heat, cool mode."""
        action = (
            HVACAction.OFF if self.preset_mode == PRESET_NONE else HVACAction.HEATING
        )
        return action

class Glowv1Thermostat(HeatzyPiloteV2Thermostat):
    """Glow."""
    #DEROG_MODE = 1 is PROGRAM Mode
    #DEROG_MODE = 2 is VACATION Mode

    _attr_supported_features = SUPPORT_PRESET_MODE | SUPPORT_TARGET_TEMPERATURE_RANGE | SUPPORT_TARGET_TEMPERATURE

    @property
    def current_temperature(self) -> float:
        """Return current temperature."""
        cur_tempH = (
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CUR_TEMP_H)
        )
        cur_tempL = (
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CUR_TEMP_L)
        )
        return (cur_tempL + (cur_tempH * 256)) / 10

    @property
    def target_temperature_high(self) -> float:
        """Return comfort temperature."""
        cft_tempH = (
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CFT_TEMP_H, 0)
        )
        cft_tempL = (
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CFT_TEMP_L, 0)
        )
        return (cft_tempL + (cft_tempH * 256)) / 10

    @property
    def target_temperature_low(self) -> float:
        """Return comfort temperature."""
        eco_tempH = (
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(ECO_TEMP_H, 0)
        )
        eco_tempL = (
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(ECO_TEMP_L, 0)
        )
        return (eco_tempL + (eco_tempH * 256)) / 10

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temp_eco = kwargs.get(ATTR_TARGET_TEMP_LOW)
        temp_cft = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        if (temp_eco or temp_cft) is None:
            return

        b_temp_cft = int(temp_cft * 10)
        b_temp_eco = int(temp_eco * 10)

        self.coordinator.data[self.unique_id].get(CONF_ATTR, {})[
            ECO_TEMP_L
        ] = b_temp_eco
        self.coordinator.data[self.unique_id].get(CONF_ATTR, {})[
            CFT_TEMP_L
        ] = b_temp_cft

        try:
            await self.coordinator.api.async_control_device(
                self.unique_id,
                {
                    CONF_ATTRS: {
                        CFT_TEMP_L: b_temp_cft,
                        ECO_TEMP_L: b_temp_eco,
                    }
                },
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Error to set temperature: %s", error)

    async def async_turn_on(self) -> str:
        """Turn device on."""
        #When turning ON we set to Comfort preset and we also ensure PROGRAM and VACATION mode are OFF
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_ON_OFF: 1, CONF_MODE: "cft", CONF_DEROG_MODE: 0}}
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Error to turn on : %s", error)

    async def async_turn_off(self) -> str:
        """Turn device off."""
        #When turning OFF we also ensure PROGRAM and VACATION mode are OFF
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_ON_OFF: 0, CONF_DEROG_MODE: 0}}
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Error to turn off : %s", error)

    async def async_turn_auto(self) -> str:
        """Turn device off."""
        #When setting to PROGRAM Mode we also ensure it's turned ON
        try:
            await self.coordinator.api.async_control_device(
                self.unique_id, {CONF_ATTRS: {CONF_ON_OFF: 1, CONF_DEROG_MODE: 1}}
            )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Error to turn off : %s", error)

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        #If OFF...
        if (
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_ON_OFF) == 0
        ):
            # but in VACATION mode then set HVAC Mode to HEAT
            if (
                self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_DEROG_MODE) == 2
            ):
                return HVACMode.HEAT
            # otherwise  set HVAC Mode to OFF
            else:
                return HVACMode.OFF

        #Otherwise if in PROGRAM mode set HVAC Mode to AUTO
        elif (
              self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_DEROG_MODE) == 1
        ):
            return HVACMode.AUTO
        #Otherwise set HVAC Mode to HEAT
        return HVACMode.HEAT

    @property
    def target_temperature(self):
        """Return target temperature for mode."""
        #Target temp is set to Low/High/Away value according to the current [preset] mode
        if self.preset_mode == PRESET_ECO:
           return self.target_temperature_low
        if self.preset_mode == PRESET_COMFORT:
           return self.target_temperature_high
        if self.preset_mode == PRESET_AWAY:
           return FROST_TEMP

    @property
    def hvac_action(self):
        """Return hvac action ie. heat, cool mode."""
        #If OFF then set HVAC Action to OFF
        if self.preset_mode == PRESET_NONE:
            return HVACAction.OFF
        #If Target temp is higher than current temp then set HVAC Action to HEATING
        elif self.target_temperature > self.current_temperature:
            return HVACAction.HEATING
        #Otherwise set to IDEL
        return HVACAction.IDLE

    async def async_set_hvac_mode(self, hvac_mode: str) -> bool:
        """Set new hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        elif hvac_mode == HVACMode.AUTO:
            await self.async_turn_auto()
        elif hvac_mode == HVACMode.HEAT:
            await self.async_turn_on()

    # spell-checker:disable
    HEATZY_TO_HA_STATE = {
        0: PRESET_COMFORT,
        1: PRESET_ECO,
        2: PRESET_AWAY
    }

    HA_TO_HEATZY_STATE = {
        PRESET_COMFORT: "cft",
        PRESET_ECO: "eco",
        PRESET_AWAY: "fro",
        PRESET_NONE: "fro", #must be cft/eco/fro, stop not allowed
    }

    HA_TO_HEATZY_ON_OFF = {
        PRESET_COMFORT: 1,
        PRESET_ECO: 1,
        PRESET_AWAY: 1,
        PRESET_NONE: 0,
    }
    # spell-checker:enable

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode, e.g., home, away, temp."""
        if self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_ON_OFF) == 0:
           #If OFF but in VACATION mode then set PRESET mode to AWAY
           if self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_DEROG_MODE) == 2:
               return PRESET_AWAY
           #If OFF then report as NONE
           return PRESET_NONE
        #Use CUR_MODE for mapping to preset mode as this works in PROGRAM mode as well manual mode
        return self.HEATZY_TO_HA_STATE.get(
            self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_CUR_MODE)
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        #When preset mode is changed we explicitly set to Manual Mode (DEROG_MODE=0)
        try:
            #If in VACATION mode then as well as setting preset mode we also stop the VACATION mode
            if self.coordinator.data[self.unique_id].get(CONF_ATTR, {}).get(CONF_DEROG_MODE) == 2:
                await self.coordinator.api.async_control_device(
                    self.unique_id,
                    {CONF_ATTRS: {CONF_MODE: self.HA_TO_HEATZY_STATE.get(preset_mode), CONF_ON_OFF: self.HA_TO_HEATZY_ON_OFF.get(preset_mode), CONF_DEROG_MODE: 0}},
                )
            #If not in VACATION mode then we just set the preset mode (so if in PROGRAM mode it will remain in PROGRAM mode with preset mode updated until next schedule change
            else:
                await self.coordinator.api.async_control_device(
                    self.unique_id,
                    {CONF_ATTRS: {CONF_MODE: self.HA_TO_HEATZY_STATE.get(preset_mode), CONF_ON_OFF: self.HA_TO_HEATZY_ON_OFF.get(preset_mode)}},
                )
            await self.coordinator.async_request_refresh()
        except HeatzyException as error:
            _LOGGER.error("Set preset mode (%s) %s (%s)", preset_mode, error, self.name)
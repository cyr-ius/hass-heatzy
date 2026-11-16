"""Switch for Heatzy."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatzyConfigEntry
from .const import (
    BLOOM,
    CONF_ATTRS,
    CONF_DEROG_MODE,
    CONF_LOCK,
    CONF_LOCK_OTHER,
    CONF_PRODUCT_KEY,
    CONF_WINDOW,
    GLOW,
    PILOTE_PRO_V1,
    PILOTE_V2,
    PILOTE_V3,
    PILOTE_V4,
)
from .entity import HeatzyEntity

# Data comes from the coordinator; actions are not limited.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class HeatzySwitchEntityDescription(SwitchEntityDescription):
    """Represents an Flow Sensor."""

    attr: str
    products: list[str]
    value_fn: Callable[..., Any]
    cls: Callable[..., Any] = lambda *args: HeatzySwitch(*args)


SWITCH_TYPES: Final[tuple[HeatzySwitchEntityDescription, ...]] = (
    HeatzySwitchEntityDescription(
        key="lock",
        translation_key="lock",
        products=PILOTE_V2 + PILOTE_V3 + PILOTE_V4 + BLOOM + PILOTE_PRO_V1,
        attr=CONF_LOCK,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda attrs: attrs.get(CONF_LOCK) == 1,
    ),
    HeatzySwitchEntityDescription(
        key="lock",
        translation_key="lock",
        products=GLOW,
        attr=CONF_LOCK_OTHER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda attrs: attrs.get(CONF_LOCK_OTHER) == 1,
    ),
    HeatzySwitchEntityDescription(
        key="window",
        translation_key="window",
        products=PILOTE_PRO_V1,
        attr=CONF_WINDOW,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda attrs: attrs.get(CONF_WINDOW) == 1,
    ),
    HeatzySwitchEntityDescription(
        key="presence_enabled",
        translation_key="presence_enabled",
        products=PILOTE_PRO_V1,
        attr=CONF_DEROG_MODE,
        entity_category=EntityCategory.CONFIG,
        cls=lambda *args: PresenceSwitch(*args),
        value_fn=lambda attrs: attrs.get(CONF_DEROG_MODE) == 3,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatzyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set the sensor platform."""
    coordinator = entry.runtime_data
    entities = []

    for unique_id, device in coordinator.data.items():
        product_key = device.get(CONF_PRODUCT_KEY)
        for description in SWITCH_TYPES:
            cls = description.cls
            if product_key in description.products:
                entities.extend([cls(coordinator, description, unique_id)])

    async_add_entities(entities)


class HeatzySwitch(HeatzyEntity, SwitchEntity):
    """Switch."""

    entity_description: HeatzySwitchEntityDescription

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.entity_description.value_fn(self._attrs)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        config = {CONF_ATTRS: {self.entity_description.attr: 1}}
        await self._handle_action(config)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        config = {CONF_ATTRS: {self.entity_description.attr: 0}}
        await self._handle_action(config)


class PresenceSwitch(HeatzySwitch):
    """Heatzy presence."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        config = {CONF_ATTRS: {self.entity_description.attr: 3}}
        await self._handle_action(config)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        config = {CONF_ATTRS: {self.entity_description.attr: 0}}
        await self._handle_action(config)

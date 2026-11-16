"""Services for the Heatzy integration."""

import voluptuous as vol

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import CONF_DELAY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import service

from .const import DOMAIN

# derog_time is stored on one byte by the module (see services.yaml)
DELAY_SCHEMA = vol.All(vol.Coerce(int), vol.Range(min=1, max=255))

SERVICES: tuple[tuple[str, dict, str], ...] = (
    ("boost", {vol.Required(CONF_DELAY): DELAY_SCHEMA}, "_async_boost_mode"),
    ("vacation", {vol.Required(CONF_DELAY): DELAY_SCHEMA}, "_async_vacation_mode"),
    ("presence", {}, "_async_presence_detection"),
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Heatzy entity services on the climate platform."""
    for name, schema, method in SERVICES:
        service.async_register_platform_entity_service(
            hass,
            DOMAIN,
            name,
            entity_domain=CLIMATE_DOMAIN,
            schema=schema,
            func=method,
        )

"""Crestron TSW Home Assistant integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_IP_ID,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_ANALOG,
    SERVICE_SET_DIGITAL,
    SERVICE_SET_SERIAL,
)
from .runtime import CrestronTSWRuntime

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
JOIN_SCHEMA = vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up global feedback services."""
    hass.data.setdefault(DOMAIN, {})

    def runtime_for_call(call: ServiceCall) -> CrestronTSWRuntime:
        runtimes = hass.data.get(DOMAIN, {})
        if not runtimes:
            raise HomeAssistantError("No Crestron TSW integration is configured")
        return next(iter(runtimes.values()))

    async def set_digital(call: ServiceCall) -> None:
        runtime_for_call(call).send_feedback("digital", call.data["join"], call.data["value"])

    async def set_analog(call: ServiceCall) -> None:
        runtime_for_call(call).send_feedback("analog", call.data["join"], call.data["value"])

    async def set_serial(call: ServiceCall) -> None:
        runtime_for_call(call).send_feedback("serial", call.data["join"], call.data["value"])

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DIGITAL,
        set_digital,
        schema=vol.Schema({vol.Required("join"): JOIN_SCHEMA, vol.Required("value"): cv.boolean}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ANALOG,
        set_analog,
        schema=vol.Schema(
            {
                vol.Required("join"): JOIN_SCHEMA,
                vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SERIAL,
        set_serial,
        schema=vol.Schema({vol.Required("join"): JOIN_SCHEMA, vol.Required("value"): cv.string}),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a configured CIP listener."""
    runtime = CrestronTSWRuntime(
        hass,
        entry.entry_id,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_IP_ID],
    )
    try:
        await runtime.async_start()
    except OSError as err:
        raise ConfigEntryNotReady(
            f"Could not listen on {entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}: {err}"
        ) from err

    hass.data[DOMAIN][entry.entry_id] = runtime
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="Crestron",
        model="TSW-750",
        name=entry.data[CONF_NAME],
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration and close TCP 41794."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    runtime: CrestronTSWRuntime = hass.data[DOMAIN].pop(entry.entry_id)
    await runtime.async_stop()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

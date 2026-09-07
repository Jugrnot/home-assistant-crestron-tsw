"""Device automation triggers for Crestron TSW buttons."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo

from .const import ATTR_ENTRY_ID, ATTR_JOIN, ATTR_PRESSED, DOMAIN, EVENT_BUTTON, JOIN_NAMES

CONF_SUBTYPE = "subtype"
TRIGGER_TYPE = "button_short_press"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In([TRIGGER_TYPE]),
        vol.Required(CONF_SUBTYPE): cv.string,
    }
)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    device = dr.async_get(hass).async_get(device_id)
    if device is None or not any(
        entry_id in hass.data.get(DOMAIN, {}) for entry_id in device.config_entries
    ):
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: TRIGGER_TYPE,
            CONF_SUBTYPE: str(join),
        }
        for join in JOIN_NAMES
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: dict[str, Any],
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    config = TRIGGER_SCHEMA(config)
    device = dr.async_get(hass).async_get(config[CONF_DEVICE_ID])
    if device is None:
        raise vol.Invalid("Crestron TSW device not found")
    entry_id = next(
        (entry for entry in device.config_entries if entry in hass.data.get(DOMAIN, {})),
        None,
    )
    if entry_id is None:
        raise vol.Invalid("Crestron TSW config entry not loaded")
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_BUTTON,
            event_trigger.CONF_EVENT_DATA: {
                ATTR_ENTRY_ID: entry_id,
                ATTR_JOIN: int(config[CONF_SUBTYPE]),
                ATTR_PRESSED: True,
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: dict[str, Any]
) -> dict[str, vol.Schema]:
    return {"extra_fields": vol.Schema({})}

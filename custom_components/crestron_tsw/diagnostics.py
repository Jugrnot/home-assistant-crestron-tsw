"""Diagnostics support for Crestron TSW."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .runtime import CrestronTSWRuntime


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    runtime: CrestronTSWRuntime = hass.data[DOMAIN][entry.entry_id]
    return {
        "config": {
            "listen_host": entry.data["host"],
            "listen_port": entry.data["port"],
            "ip_id": entry.data["ip_id"],
        },
        "connected": runtime.connected,
        "remote_address": runtime.remote_address,
        "cached_feedback_joins": sorted(
            f"{join_type}/{join}" for join_type, join in runtime.feedback
        ),
    }

"""Entity base class for Crestron TSW."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .runtime import CrestronTSWRuntime


class CrestronTSWEntity(Entity):
    """Base entity attached to the configured panel."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, runtime: CrestronTSWRuntime) -> None:
        self.entry = entry
        self.runtime = runtime
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

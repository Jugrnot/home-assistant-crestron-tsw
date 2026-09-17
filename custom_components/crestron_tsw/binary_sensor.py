"""Connection sensor for Crestron TSW."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_CONNECTION
from .entity import CrestronTSWEntity
from .runtime import CrestronTSWRuntime


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime: CrestronTSWRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CrestronConnectedSensor(entry, runtime)])


class CrestronConnectedSensor(CrestronTSWEntity, BinarySensorEntity):
    """Show whether the touch panel is connected to Home Assistant."""

    _attr_name = "Connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, entry: ConfigEntry, runtime: CrestronTSWRuntime) -> None:
        super().__init__(entry, runtime)
        self._attr_unique_id = f"{entry.entry_id}_connection"

    @property
    def is_on(self) -> bool:
        return self.runtime.connected

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"remote_address": self.runtime.remote_address}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_CONNECTION}_{self.entry.entry_id}",
                self._connection_changed,
            )
        )

    @callback
    def _connection_changed(self, _connected: bool) -> None:
        self.async_write_ha_state()

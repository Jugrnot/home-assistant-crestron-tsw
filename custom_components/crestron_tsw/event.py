"""Button event entities for Crestron TSW."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .cip import CIPJoinEvent
from .const import DOMAIN, JOIN_NAMES, SIGNAL_JOIN
from .entity import CrestronTSWEntity
from .runtime import CrestronTSWRuntime


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime: CrestronTSWRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CrestronJoinEventEntity(entry, runtime, join, name) for join, name in JOIN_NAMES.items()
    )


class CrestronJoinEventEntity(CrestronTSWEntity, EventEntity):
    """Represent press/release events from one digital join."""

    _attr_event_types: ClassVar[list[str]] = ["pressed", "released"]

    def __init__(
        self,
        entry: ConfigEntry,
        runtime: CrestronTSWRuntime,
        join: int,
        name: str,
    ) -> None:
        super().__init__(entry, runtime)
        self.join = join
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_join_{join}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_JOIN}_{self.entry.entry_id}",
                self._handle_join,
            )
        )

    def _handle_join(self, event: CIPJoinEvent) -> None:
        if event.type != "digital" or event.join != self.join:
            return
        self._trigger_event(
            "pressed" if event.value else "released",
            {"join": self.join, "value": event.value},
        )
        self.async_write_ha_state()

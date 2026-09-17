"""Home Assistant runtime for a Crestron TSW panel."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .cip import CIPJoinEvent, CIPServer
from .const import (
    ATTR_ENTRY_ID,
    ATTR_JOIN,
    ATTR_NAME,
    ATTR_PRESSED,
    ATTR_TYPE,
    ATTR_VALUE,
    EVENT_BUTTON,
    EVENT_JOIN,
    JOIN_NAMES,
    SIGNAL_CONNECTION,
    SIGNAL_JOIN,
)


class CrestronTSWRuntime:
    """Own the CIP listener and translate protocol events into HA events."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        host: str,
        port: int,
        ip_id: int,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.feedback: dict[tuple[str, int], bool | int | str] = {}
        self.server = CIPServer(
            host,
            port,
            ip_id,
            self._handle_join,
            self._handle_connection,
            self._handle_ready,
        )

    @property
    def connected(self) -> bool:
        return self.server.connected

    @property
    def remote_address(self) -> str | None:
        return self.server.remote_address

    async def async_start(self) -> None:
        await self.server.start()

    async def async_stop(self) -> None:
        await self.server.stop()

    def _handle_connection(self, connected: bool, remote_address: str | None) -> None:
        self.hass.loop.call_soon_threadsafe(self._async_handle_connection, connected)

    @callback
    def _async_handle_connection(self, connected: bool) -> None:
        async_dispatcher_send(self.hass, f"{SIGNAL_CONNECTION}_{self.entry_id}", connected)

    def _handle_ready(self) -> None:
        for (join_type, join), value in self.feedback.items():
            self.send_feedback(join_type, join, value, remember=False)

    def _handle_join(self, event: CIPJoinEvent) -> None:
        self.hass.loop.call_soon_threadsafe(self._async_handle_join, event)

    @callback
    def _async_handle_join(self, event: CIPJoinEvent) -> None:
        name = JOIN_NAMES.get(event.join, f"Join {event.join}")
        event_data: dict[str, Any] = {
            ATTR_ENTRY_ID: self.entry_id,
            ATTR_JOIN: event.join,
            ATTR_NAME: name,
            ATTR_TYPE: event.type,
            ATTR_VALUE: event.value,
        }
        self.hass.bus.async_fire(EVENT_JOIN, event_data)
        async_dispatcher_send(self.hass, f"{SIGNAL_JOIN}_{self.entry_id}", event)
        if event.type == "digital" and isinstance(event.value, bool):
            button_data = {
                **event_data,
                ATTR_PRESSED: event.value,
            }
            self.hass.bus.async_fire(EVENT_BUTTON, button_data)

    def send_feedback(
        self,
        join_type: str,
        join: int,
        value: bool | int | str,
        *,
        remember: bool = True,
    ) -> bool:
        if remember:
            self.feedback[(join_type, join)] = value
        if join_type == "digital":
            return self.server.send_digital(join, bool(value))
        if join_type == "analog":
            return self.server.send_analog(join, int(value))
        if join_type == "serial":
            return self.server.send_serial(join, str(value))
        raise ValueError(f"Unsupported join type: {join_type}")

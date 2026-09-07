"""Minimal asyncio Crestron Internet Protocol server used by TSW panels."""

from __future__ import annotations

import asyncio
import logging
import socket
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

ACK = 0x00
SERVER_SIGNON = 0x01
CONN_ACCEPTED = 0x02
CONN_REFUSED = 0x04
JOIN_EVENT = 0x05
CLIENT_SIGNON = 0x0A
PING = 0x0D
PONG = 0x0E
WHOIS = 0x0F
UNICODE = 0x12

DIGITAL = 0x00
DIGITAL_ALT = 0x27
TIME_SYNC = 0x08
ANALOG = 0x01
ANALOG_ALT = 0x14
SERIAL = 0x02
SERIAL_ALT = 0x12
SERIAL_ALT_2 = 0x15
UPDATE = 0x03
SERIAL_UNICODE = 0x34
SMART_OBJECT = 0x38

PING_INTERVAL = 10
MAX_MISSED_PINGS = 5


@dataclass(slots=True, frozen=True)
class CIPJoinEvent:
    """A join event received from the panel."""

    type: str
    join: int
    value: bool | int | str


def _wrap(message_type: int, payload: bytes) -> bytes:
    if len(payload) > 255:
        raise ValueError("CIP payload exceeds one-byte frame length")
    return bytes((message_type, 0, len(payload))) + payload


def join_event_frame(join_type: int, payload: bytes) -> bytes:
    """Build a CIP join event frame."""
    return _wrap(JOIN_EVENT, bytes((0, 0, len(payload) + 1, join_type)) + payload)


def digital_frame(join: int, value: bool) -> bytes:
    """Build digital feedback for a panel join."""
    _validate_join(join)
    encoded = join - 1
    high = encoded & 0xFF
    low = (encoded >> 8) | (0 if value else 0x80)
    return join_event_frame(DIGITAL, bytes((high, low)))


def analog_frame(join: int, value: int) -> bytes:
    """Build analog feedback for a panel join."""
    _validate_join(join)
    value = max(0, min(65535, int(value)))
    encoded = join - 1
    return join_event_frame(
        ANALOG_ALT,
        bytes((encoded >> 8, encoded & 0xFF, value >> 8, value & 0xFF)),
    )


def serial_frame(join: int, value: str) -> bytes:
    """Build serial feedback for a panel join."""
    _validate_join(join)
    encoded = join - 1
    return join_event_frame(
        SERIAL_ALT_2,
        bytes((encoded >> 8, encoded & 0xFF, 0x03)) + value.encode("utf-8"),
    )


def _validate_join(join: int) -> None:
    if not 1 <= join <= 65535:
        raise ValueError("join must be between 1 and 65535")


class CIPProtocolParser:
    """Incrementally parse framed CIP traffic."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        """Append bytes and return every complete top-level frame."""
        self._buffer.extend(data)
        frames: list[tuple[int, bytes]] = []
        while len(self._buffer) >= 3:
            if self._buffer[1] != 0:
                del self._buffer[0]
                continue
            length = self._buffer[2]
            total = length + 3
            if len(self._buffer) < total:
                break
            message_type = self._buffer[0]
            payload = bytes(self._buffer[3:total])
            del self._buffer[:total]
            frames.append((message_type, payload))
        return frames


def parse_join_payload(message: bytes) -> list[CIPJoinEvent]:
    """Parse a JOIN_EVENT or UNICODE payload."""
    if len(message) < 4:
        return []
    if len(message) > 5 and message[2] == 0 and message[4] == SERIAL_UNICODE:
        length = message[3]
        join_type = message[4]
        payload = message[5 : length + 4]
    else:
        length = message[2]
        join_type = message[3]
        payload = message[4 : length + 3]

    events: list[CIPJoinEvent] = []
    if join_type in (DIGITAL, DIGITAL_ALT):
        for offset in range(0, len(payload) - 1, 2):
            first, second = payload[offset : offset + 2]
            encoded = (first << 8) + second
            join = ((encoded >> 8) | ((encoded & 0x7F) << 8)) + 1
            events.append(CIPJoinEvent("digital", join, (second & 0x80) == 0))
    elif join_type in (ANALOG, ANALOG_ALT):
        width = 4 if len(payload) % 4 == 0 else 3
        for offset in range(0, len(payload), width):
            item = payload[offset : offset + width]
            if len(item) == 4:
                join = (item[0] << 8) + item[1] + 1
                value = (item[2] << 8) + item[3]
            elif len(item) == 3:
                join = item[0] + 1
                value = (item[1] << 8) + item[2]
            else:
                continue
            events.append(CIPJoinEvent("analog", join, value))
    elif join_type in (SERIAL, SERIAL_ALT, SERIAL_ALT_2, SERIAL_UNICODE) and len(payload) >= 3:
        join = (payload[0] << 8) + payload[1] + 1
        events.append(
            CIPJoinEvent(
                "serial",
                join,
                payload[3:].decode("utf-8", errors="replace"),
            )
        )
    return events


class CIPServer:
    """An asyncio TCP server impersonating a Crestron control processor."""

    def __init__(
        self,
        host: str,
        port: int,
        ip_id: int,
        event_callback: Callable[[CIPJoinEvent], None],
        connection_callback: Callable[[bool, str | None], None],
        ready_callback: Callable[[], None],
    ) -> None:
        self.host = host
        self.port = port
        self.ip_id = ip_id
        self._event_callback = event_callback
        self._connection_callback = connection_callback
        self._ready_callback = ready_callback
        self._server: asyncio.AbstractServer | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._ping_task: asyncio.Task[None] | None = None
        self._missed_pings = 0
        self._ready = False
        self.remote_address: str | None = None

    @property
    def connected(self) -> bool:
        """Return whether a panel is connected."""
        return self._writer is not None and not self._writer.is_closing()

    async def start(self) -> None:
        """Start accepting panel connections."""
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        _LOGGER.info("CIP listening on %s:%s with IP ID 0x%02X", self.host, self.port, self.ip_id)

    async def stop(self) -> None:
        """Stop the server and any active panel connection."""
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None
        if self._writer:
            self._writer.close()
            with suppress(ConnectionError):
                await self._writer.wait_closed()
            self._writer = None
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self.remote_address = None
        self._ready = False

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        if self._writer and not self._writer.is_closing():
            self._writer.close()
            with suppress(ConnectionError):
                await self._writer.wait_closed()
        self._writer = writer
        peer = writer.get_extra_info("peername")
        self.remote_address = str(peer[0]) if peer else None
        raw_socket = writer.get_extra_info("socket")
        if raw_socket:
            raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self._missed_pings = 0
        self._ready = False
        self._connection_callback(True, self.remote_address)
        self._write(bytes((WHOIS, 0, 1, 2)))
        self._ping_task = asyncio.create_task(self._ping_loop())
        parser = CIPProtocolParser()
        try:
            while data := await reader.read(4096):
                self._missed_pings = 0
                for message_type, payload in parser.feed(data):
                    await self._process_frame(message_type, payload)
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            if writer is self._writer:
                if self._ping_task:
                    self._ping_task.cancel()
                    self._ping_task = None
                writer.close()
                with suppress(ConnectionError):
                    await writer.wait_closed()
                self._writer = None
                self.remote_address = None
                self._ready = False
                self._connection_callback(False, None)

    async def _process_frame(self, message_type: int, payload: bytes) -> None:
        if message_type in (CLIENT_SIGNON, SERVER_SIGNON):
            self._write(bytes((CONN_ACCEPTED, 0, 4, 0, 0, 0, 3)))
            await asyncio.sleep(0.1)
            self._write(bytes((JOIN_EVENT, 0, 5, 0, 0, 2, UPDATE, 0)))
            self._mark_ready()
        elif message_type == CONN_ACCEPTED:
            self._write(bytes((JOIN_EVENT, 0, 5, 0, 0, 2, UPDATE, 0)))
            self._mark_ready()
        elif message_type in (JOIN_EVENT, UNICODE):
            for event in parse_join_payload(payload):
                self._event_callback(event)
        elif message_type == PING:
            self._write(bytes((PONG, 0, 2, 0, 0)))
        elif message_type == PONG:
            self._missed_pings = max(0, self._missed_pings - 1)
        elif message_type == WHOIS:
            self._write(
                bytes(
                    (
                        CLIENT_SIGNON,
                        0,
                        11,
                        0,
                        self.ip_id,
                        0xA3,
                        0x42,
                        0x40,
                        0x02,
                        0,
                        0,
                        0xD1,
                        0x01,
                        0,
                    )
                )
            )

    def _mark_ready(self) -> None:
        if self._ready:
            return
        self._ready = True
        self._ready_callback()

    async def _ping_loop(self) -> None:
        try:
            while self.connected:
                await asyncio.sleep(PING_INTERVAL)
                if self._missed_pings >= MAX_MISSED_PINGS:
                    if self._writer:
                        self._writer.close()
                    return
                self._missed_pings += 1
                self._write(bytes((PING, 0, 2, 0, 0)))
        except asyncio.CancelledError:
            return

    def _write(self, data: bytes) -> bool:
        if not self.connected or not self._writer:
            return False
        self._writer.write(data)
        return True

    def send_digital(self, join: int, value: bool) -> bool:
        """Send digital feedback."""
        return self._write(digital_frame(join, value))

    def send_analog(self, join: int, value: int) -> bool:
        """Send analog feedback."""
        return self._write(analog_frame(join, value))

    def send_serial(self, join: int, value: str) -> bool:
        """Send serial feedback."""
        return self._write(serial_frame(join, value))

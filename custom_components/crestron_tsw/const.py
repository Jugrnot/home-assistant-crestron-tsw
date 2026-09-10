"""Constants for the Crestron TSW integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "crestron_tsw"
DEFAULT_NAME = "Crestron TSW-750"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 41794
DEFAULT_IP_ID = 0x40

CONF_IP_ID = "ip_id"

EVENT_JOIN = "crestron_tsw_join"
EVENT_BUTTON = "crestron_tsw_button"
ATTR_ENTRY_ID = "entry_id"
ATTR_JOIN = "join"
ATTR_NAME = "name"
ATTR_TYPE = "type"
ATTR_VALUE = "value"
ATTR_PRESSED = "pressed"

SERVICE_SET_DIGITAL = "set_digital_feedback"
SERVICE_SET_ANALOG = "set_analog_feedback"
SERVICE_SET_SERIAL = "set_serial_feedback"

SIGNAL_CONNECTION = f"{DOMAIN}_connection"
SIGNAL_JOIN = f"{DOMAIN}_join"

PLATFORMS = [Platform.BINARY_SENSOR, Platform.EVENT]

JOIN_NAMES: dict[int, str] = {
    1: "Hardware key 1",
    2: "Hardware key 2",
    3: "Hardware key 3",
    4: "Hardware key 4",
    5: "Hardware key 5",
    101: "Watch TV",
    102: "Apple TV",
    103: "System On",
    104: "Display / Input",
    105: "All Off",
    106: "Game Console",
    107: "Volume Up",
    108: "Volume Down",
    109: "Mute",
    110: "Music",
    111: "Play / Pause",
    201: "All Zone Stereo",
    202: "Stereo Mode",
    203: "Surround",
    204: "Multi Ch Stereo",
    205: "Direct Mode",
    206: "TV Audio",
    207: "HEOS Music",
}

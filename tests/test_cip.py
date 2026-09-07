"""Protocol tests that do not require a Home Assistant installation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).parents[1] / "custom_components" / "crestron_tsw"),
)

from cip import (
    JOIN_EVENT,
    CIPProtocolParser,
    analog_frame,
    digital_frame,
    parse_join_payload,
    serial_frame,
)


def parsed(frame: bytes):
    parser = CIPProtocolParser()
    frames = parser.feed(frame[:2])
    assert frames == []
    frames = parser.feed(frame[2:])
    assert len(frames) == 1
    message_type, payload = frames[0]
    assert message_type == JOIN_EVENT
    return parse_join_payload(payload)


class CIPProtocolTests(unittest.TestCase):
    def test_digital_round_trip(self) -> None:
        event = parsed(digital_frame(101, True))[0]
        self.assertEqual((event.type, event.join, event.value), ("digital", 101, True))
        event = parsed(digital_frame(111, False))[0]
        self.assertEqual((event.type, event.join, event.value), ("digital", 111, False))

    def test_known_digital_join_encoding(self) -> None:
        self.assertEqual(
            digital_frame(101, True),
            bytes((0x05, 0, 6, 0, 0, 3, 0, 0x64, 0)),
        )
        self.assertEqual(
            digital_frame(101, False),
            bytes((0x05, 0, 6, 0, 0, 3, 0, 0x64, 0x80)),
        )

    def test_analog_round_trip(self) -> None:
        event = parsed(analog_frame(12, 45678))[0]
        self.assertEqual((event.type, event.join, event.value), ("analog", 12, 45678))

    def test_serial_round_trip(self) -> None:
        event = parsed(serial_frame(7, "Living room"))[0]
        self.assertEqual((event.type, event.join, event.value), ("serial", 7, "Living room"))

    def test_parser_handles_multiple_frames(self) -> None:
        parser = CIPProtocolParser()
        frames = parser.feed(digital_frame(101, True) + analog_frame(12, 42))
        self.assertEqual([item[0] for item in frames], [JOIN_EVENT, JOIN_EVENT])

    def test_clamps_analog_feedback(self) -> None:
        event = parsed(analog_frame(1, 999999))[0]
        self.assertEqual(event.value, 65535)


if __name__ == "__main__":
    unittest.main()

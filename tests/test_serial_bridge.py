import sys
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))

import serial_bridge  # noqa: E402


class SerialBridgeTests(unittest.TestCase):
    def test_records_sensor_telemetry(self) -> None:
        self.assertTrue(serial_bridge._record_telemetry("9042,17.5;"))
        self.assertEqual(serial_bridge.get_recent_values(9042)[-1], "17.5")

    def test_leaves_command_responses_unconsumed(self) -> None:
        self.assertFalse(serial_bridge._record_telemetry("OK"))

    def test_identifies_expired_commands(self) -> None:
        self.assertTrue(
            serial_bridge._command_expired({"deadline": time.monotonic() - 1})
        )
        self.assertFalse(
            serial_bridge._command_expired({"deadline": time.monotonic() + 1})
        )


if __name__ == "__main__":
    unittest.main()

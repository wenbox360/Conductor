import os
import time
from pathlib import Path

import serial
from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env.local"))

SERIAL_PORT = os.getenv("SERIAL_PORT", "").strip()
BAUD_RATE = int(os.getenv("BAUD_RATE", "9600"))


def main() -> None:
    """Send a short buzzer command to verify the serial connection."""
    if not SERIAL_PORT:
        raise SystemExit("Set SERIAL_PORT in mcp-server/.env.local first")
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as connection:
        time.sleep(2)
        connection.write(b"2,500;\n")
        time.sleep(0.2)
        print("Response:", connection.readline().decode(errors="replace").strip())


if __name__ == "__main__":
    main()

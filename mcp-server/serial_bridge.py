import os
import logging
import threading
import time
from collections import defaultdict, deque
from queue import Empty, Queue
from typing import Any

import serial
from serial import SerialException


logger = logging.getLogger(__name__)

SERIAL_PORT = os.getenv("SERIAL_PORT", "").strip()
BAUD_RATE = int(os.getenv("BAUD_RATE", "9600"))
MAX_RECENT_VALUES = int(os.getenv("MAX_RECENT_VALUES", "10"))

command_queue: Queue[dict[str, Any]] = Queue()
responses: dict[str, str | None] = {}
_responses_lock = threading.Lock()

_recent_values: defaultdict[int, deque[str]] = defaultdict(
    lambda: deque(maxlen=MAX_RECENT_VALUES)
)
_values_lock = threading.Lock()
_serial: serial.Serial | None = None
_processor_started = False
_processor_lock = threading.Lock()


def add_command_to_queue(command: dict[str, Any]) -> None:
    """Queue a hardware command for the serial worker."""
    command_queue.put(command)


def is_serial_configured() -> bool:
    """Return whether a serial device path was configured."""
    return bool(SERIAL_PORT)


def _command_expired(command: dict[str, Any]) -> bool:
    deadline = command.get("deadline")
    return deadline is not None and time.monotonic() >= float(deadline)


def get_recent_values(sensor_id: int) -> list[str]:
    """Return a snapshot of recent telemetry for a sensor ID."""
    with _values_lock:
        return list(_recent_values.get(sensor_id, ()))


def pop_response(response_key: str) -> str | None:
    """Return and remove a completed command response."""
    with _responses_lock:
        return responses.pop(response_key, None)


def _record_telemetry(line: str) -> bool:
    """Record an `id,value` telemetry line and report whether it matched."""
    payload = line.strip().rstrip(";")
    if "," not in payload:
        return False

    sensor_id_text, value = payload.split(",", 1)
    try:
        sensor_id = int(sensor_id_text)
    except ValueError:
        return False

    with _values_lock:
        _recent_values[sensor_id].append(value.strip())
    return True


def _open_serial() -> serial.Serial | None:
    global _serial

    if _serial is not None and _serial.is_open:
        return _serial

    try:
        _serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)
        return _serial
    except (OSError, SerialException) as error:
        logger.warning("Unable to open serial port %s: %s", SERIAL_PORT, error)
        _serial = None
        return None


def _close_serial() -> None:
    global _serial
    if _serial is not None:
        try:
            _serial.close()
        except SerialException:
            pass
    _serial = None


def _read_line(connection: serial.Serial) -> str:
    raw = connection.readline()
    return raw.decode("utf-8", errors="replace").strip()


def _read_response(connection: serial.Serial, timeout: float = 1.0) -> str | None:
    """Read a command response while retaining interleaved telemetry lines."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = _read_line(connection)
        if not line:
            continue
        if not _record_telemetry(line):
            return line
    return None


def _send_command(connection: serial.Serial, command: dict[str, Any]) -> str | None:
    command_id = command.get("command")
    value = command.get("value", "")
    payload = f"{command_id},{value};\n"

    connection.write(payload.encode("utf-8"))
    connection.flush()
    deadline = command.get("deadline")
    timeout = (
        max(0.1, float(deadline) - time.monotonic())
        if deadline is not None
        else 1.0
    )
    return _read_response(connection, timeout=timeout)


def _processor_loop() -> None:
    retry_delay = 1.0
    while True:
        connection = _open_serial()
        if connection is None:
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30.0)
            continue
        retry_delay = 1.0

        try:
            try:
                command = command_queue.get(timeout=0.05)
            except Empty:
                line = _read_line(connection)
                if line:
                    _record_telemetry(line)
                continue

            try:
                if _command_expired(command):
                    continue
                response = _send_command(connection, command)
                response_key = command.get("response_key")
                if response_key and response is not None:
                    with _responses_lock:
                        responses[response_key] = response
            finally:
                command_queue.task_done()
        except (OSError, SerialException) as error:
            logger.warning("Serial connection lost: %s", error)
            _close_serial()


def start_serial_bridge() -> None:
    """Start the single reader/writer thread once per process."""
    global _processor_started

    if not SERIAL_PORT:
        return

    with _processor_lock:
        if _processor_started:
            return
        _processor_started = True

    thread = threading.Thread(
        target=_processor_loop,
        name="conductor-serial-bridge",
        daemon=True,
    )
    thread.start()

# readQueue.py
import serial
import threading
import time
import subprocess
from collections import deque
import logging
from serial.serialutil import SerialException

logger = logging.getLogger("readQueue")
logging.basicConfig(level=logging.DEBUG)

SERIAL_PORT = '/dev/cu.usbmodem101'
BAUD_RATE = 9600
MAX_RECENT = 10
OPEN_RETRY_DELAY = 1.0  # seconds to wait before trying to reopen after error

_recent_lock = threading.Lock()
_recent_values = {}           # internal only
_stop_event = threading.Event()
_reader_thread = None

def _who_holds_port(port):
    try:
        out = subprocess.check_output(['lsof', port], stderr=subprocess.DEVNULL, text=True)
        return out.strip()
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        return None

def _process_raw(raw: str):
    """Parse 'id,value' into (int, value). Defensive - leaves value as str if not numeric."""
    parts = raw.split(',', 1)
    if len(parts) != 2:
        raise ValueError("no comma in packet")
    id_s, val_s = parts[0].strip(), parts[1].strip()
    id_int = int(id_s)
    try:
        if '.' in val_s:
            val = float(val_s)
        else:
            val = int(val_s)
    except Exception:
        val = val_s
    return id_int, val

def _open_serial():
    """Try to open serial port once and return Serial or raise."""
    return serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.5)

def _reader_loop():
    logger.info("Serial reader loop starting (port=%s)", SERIAL_PORT)
    while not _stop_event.is_set():
        ser = None
        try:
            try:
                ser = _open_serial()
                logger.info("Opened serial port %s @ %d", SERIAL_PORT, BAUD_RATE)
            except SerialException as e:
                msg = str(e)
                logger.warning("Could not open serial port: %s", msg)
                if 'Resource busy' in msg or 'Device busy' in msg or 'Errno 16' in msg:
                    holder = _who_holds_port(SERIAL_PORT)
                    if holder:
                        logger.warning("Port appears held by:\n%s", holder)
                time.sleep(OPEN_RETRY_DELAY)
                continue

            buf = bytearray()
            while not _stop_event.is_set():
                try:
                    chunk = ser.read(256)
                except SerialException as e:
                    # Device reports readiness but returned nothing -> treat as transient disconnect
                    logger.warning("Serial read error (read call): %s", e)
                    break
                if not chunk:
                    # nothing available; small sleep so we don't busy-loop
                    time.sleep(0.01)
                    continue
                buf.extend(chunk)
                # accept semicolon or newline terminated packets
                while True:
                    idx_sem = buf.find(b';')
                    idx_nl = buf.find(b'\n')
                    pos = idx_sem if (0 <= idx_sem < (idx_nl if idx_nl >=0 else float('inf'))) else idx_nl
                    if pos == -1:
                        break
                    raw = bytes(buf[:pos]).decode('utf-8', errors='replace').strip()
                    del buf[:pos+1]
                    if not raw:
                        continue
                    try:
                        id_int, value = _process_raw(raw)
                        with _recent_lock:
                            if id_int not in _recent_values:
                                _recent_values[id_int] = deque(maxlen=MAX_RECENT)
                            _recent_values[id_int].append(value)
                        logger.debug("Got id=%s value=%s", id_int, value)
                    except Exception as e:
                        logger.warning("Failed to parse '%s': %s", raw, e)

        except Exception:
            logger.exception("Unhandled exception in serial reader loop")
        finally:
            if ser:
                try:
                    ser.close()
                except Exception:
                    pass
            logger.info("Serial reader: port closed / will retry in %s sec", OPEN_RETRY_DELAY)
            time.sleep(OPEN_RETRY_DELAY)

    logger.info("Serial reader loop exiting (stop event set)")

def start_read_queue():
    global _reader_thread
    if _reader_thread and _reader_thread.is_alive():
        logger.info("Serial reader already running")
        return
    _stop_event.clear()
    _reader_thread = threading.Thread(target=_reader_loop, name="serial-read-thread", daemon=True)
    _reader_thread.start()
    logger.info("Started serial reader thread")

def stop_read_queue():
    _stop_event.set()
    if _reader_thread:
        _reader_thread.join(timeout=2.0)

def get_recent_values(id_int):
    """Return a copy of recent values for id_int (most-recent last)."""
    with _recent_lock:
        dq = _recent_values.get(id_int)
        return list(dq) if dq is not None else []

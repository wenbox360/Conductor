# tools.py
from fastmcp import FastMCP, Context
from typing import Dict, Any
from sendQueue import add_command_to_queue, responses
import asyncio
import uuid

# --- Tool implementations (not decorated) ---


async def piezo_beep_impl(context, duration: int = 500):
    if duration <= 0:
        return {"error": "duration must be > 0"}
    response_key = f"beep_{uuid.uuid4().hex[:8]}"
    command = {"command": 2, "value": duration, "response_key": response_key}
    add_command_to_queue(command)

    timeout = 3.0
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < timeout:
        resp = responses.get(response_key)
        if resp is not None:
            return {"message": f"Sent beep for {duration}ms", "response": resp}
        await asyncio.sleep(0.05)

    return {"message": f"Sent beep for {duration}ms", "response": None, "warning": "no response from Arduino (timeout)"}


async def control_servo_impl(context: Context, position: int) -> Dict[str, Any]:
    """Control servo motor position - position in degrees (0-180)."""
    if not 0 <= position <= 180:
        return {"error": "Position must be between 0 and 180 degrees"}
    servo_command_id = 20
    response_key = f"servo_{uuid.uuid4().hex[:8]}"
    command = {"command": servo_command_id, "value": position, "response_key": response_key}
    add_command_to_queue(command)

    timeout = 10.0
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < timeout:
        resp = responses.get(response_key)
        if resp is not None:
            return {"message": f"Servo set to {position} degrees", "position": position, "response": resp}
        await asyncio.sleep(0.05)

    return {
        "message": f"Servo set to {position} degrees",
        "position": position,
        "response": None,
        "warning": "no response from Arduino (timeout)"
    }


# --- Registry of all tools with their hardware dependency ---
TOOL_SPECS = [
    {"name": "piezo_beep", "impl": piezo_beep_impl, "hardware": "Piezo Buzzer"},
    {"name": "control_servo", "impl": control_servo_impl, "hardware": "Micro Servo - SG90"},
]


# --- Registration function ---

def register_tools(mcp: FastMCP, available_hardware: set[str]):
    """Enable/disable tools based on available_hardware."""
    for spec in TOOL_SPECS:
        enabled = spec["hardware"] in available_hardware
        if enabled:
            mcp.tool(enabled=enabled)(spec["impl"])
            print(f"Registered {spec['name']} enabled={enabled}")

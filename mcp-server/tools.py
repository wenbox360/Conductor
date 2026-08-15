from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Dict, Any
from serial_bridge import add_command_to_queue, is_serial_configured, pop_response
import asyncio
import uuid

# --- Tool implementations (not decorated) ---


async def piezo_beep_impl(
    context: Context,
    duration: Annotated[int, Field(ge=1, le=5000)] = 500,
):
    if not 1 <= duration <= 5000:
        raise ToolError("duration must be between 1 and 5000 milliseconds")
    if not is_serial_configured():
        raise ToolError("SERIAL_PORT is not configured")
    timeout = 3.0
    response_key = f"beep_{uuid.uuid4().hex[:8]}"
    command = {
        "command": 2,
        "value": duration,
        "response_key": response_key,
        "deadline": asyncio.get_running_loop().time() + timeout,
    }
    add_command_to_queue(command)

    start = asyncio.get_running_loop().time()
    while (asyncio.get_running_loop().time() - start) < timeout:
        resp = pop_response(response_key)
        if resp is not None:
            return {"message": f"Sent beep for {duration}ms", "response": resp}
        await asyncio.sleep(0.05)

    raise ToolError("Arduino did not acknowledge the beep command")


async def control_servo_impl(
    context: Context,
    position: Annotated[int, Field(ge=0, le=180)],
) -> Dict[str, Any]:
    """Control servo motor position - position in degrees (0-180)."""
    if not 0 <= position <= 180:
        raise ToolError("position must be between 0 and 180 degrees")
    if not is_serial_configured():
        raise ToolError("SERIAL_PORT is not configured")
    timeout = 10.0
    servo_command_id = 20
    response_key = f"servo_{uuid.uuid4().hex[:8]}"
    command = {
        "command": servo_command_id,
        "value": position,
        "response_key": response_key,
        "deadline": asyncio.get_running_loop().time() + timeout,
    }
    add_command_to_queue(command)

    start = asyncio.get_running_loop().time()
    while (asyncio.get_running_loop().time() - start) < timeout:
        resp = pop_response(response_key)
        if resp is not None:
            return {"message": f"Servo set to {position} degrees", "position": position, "response": resp}
        await asyncio.sleep(0.05)

    raise ToolError("Arduino did not acknowledge the servo command")


# --- Registry of all tools with their hardware dependency ---
TOOL_SPECS = [
    {"name": "piezo_beep", "impl": piezo_beep_impl, "hardware": "Piezo_Buzzer"},
    {"name": "control_servo", "impl": control_servo_impl, "hardware": "Micro_Servo_SG90"},
]


# --- Registration function ---

def register_tools(mcp: FastMCP, available_hardware: set[str]):
    """Register tools backed by the currently configured hardware."""
    for spec in TOOL_SPECS:
        if spec["hardware"] in available_hardware:
            mcp.tool(name=spec["name"])(spec["impl"])

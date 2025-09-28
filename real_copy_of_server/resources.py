# resources.py
import uuid
import time
from typing import Dict, Any
from fastmcp import FastMCP, Context
from readQueue import get_recent_values
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# --- Resource implementations (not decorated) ---

async def ir_distance_impl(context: Context) -> str:
    """Get reading from Sharp GP2Y0A21YK0F IR distance sensor (returns cm)."""
    # pull recent values (implementation of get_recent_values is in readQueue)
    logger.info("Fetching recent values for IR sensor")
    values = get_recent_values(40)
    logger.info(values)
    if not values:
        return "No value"

    # take last up to 10 values and average them
    last_10 = values[-10:] if len(values) >= 10 else values
    try:
        # convert readings to float and average
        avg = sum(float(v) for v in last_10) / len(last_10)
        return f"{avg:.2f} cm"
    except Exception:
        return "Invalid value(s)"


async def temp_lm35_impl(context: Context) -> str:
    """Get reading from LM35 temperature sensor (returns °C)."""
    values = get_recent_values(50)
    if not values:
        return "No value"

    last_5 = values[-5:] if len(values) >= 5 else values
    try:
        avg = sum(float(v) for v in last_5) / len(last_5)
        return f"{avg:.2f} °C"
    except Exception:
        return "Invalid value(s)"


async def ultrasonic_hcsr04_impl(context: Context) -> str:
    """Get reading from HC-SR04 ultrasonic sensor (returns cm)."""
    values = get_recent_values(60)
    if not values:
        return "No value"

    last_8 = values[-8:] if len(values) >= 8 else values
    try:
        avg = sum(float(v) for v in last_8) / len(last_8)
        return f"{avg:.2f} cm"
    except Exception:
        return "Invalid value(s)"


# --- Registry of all resources with their hardware dependency ---
RESOURCE_SPECS = [
    {
        "name": "ir_distance",
        "uri": "sensor://ir/GP2Y0A21YK0F",
        "impl": ir_distance_impl,
        "hardware": "IR-GP2Y0A21YK0F",
    },
    {
        "name": "temp_lm35",
        "uri": "sensor://temp/LM35",
        "impl": temp_lm35_impl,
        "hardware": "LM35",
    },
    {
        "name": "ultrasonic_distance",
        "uri": "sensor://ultrasonic/HC-SR04",
        "impl": ultrasonic_hcsr04_impl,
        "hardware": "HC-SR04",
    },
]


# --- Registration function ---

def register_resources(mcp: FastMCP, available_hardware: set[str]):
    """Enable/disable resources based on available_hardware and register them with the MCP server."""
    for spec in RESOURCE_SPECS:
        enabled = spec["hardware"] in available_hardware
        # register the resource with the MCP; mcp.resource returns a decorator
        mcp.resource(spec["uri"], enabled=enabled)(spec["impl"])
        print(f"Registered resource {spec['name']} uri={spec['uri']} enabled={enabled}")

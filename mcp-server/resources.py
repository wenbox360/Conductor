import logging

from fastmcp import FastMCP, Context

from serial_bridge import get_recent_values

logger = logging.getLogger(__name__)

# --- Resource implementations (not decorated) ---

async def ir_distance_impl(context: Context) -> str:
    """Get reading from Sharp GP2Y0A21YK0F IR distance sensor (returns cm)."""
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


# --- Registry of all resources with their hardware dependency ---
RESOURCE_SPECS = [
    {
        "name": "ir_distance",
        "uri": "sensor://ir/GP2Y0A21YK0F",
        "impl": ir_distance_impl,
        "hardware": "IR_GP2Y0A21YK0F",
    },
]


# --- Registration function ---

def register_resources(mcp: FastMCP, available_hardware: set[str]):
    """Register resources backed by the currently configured hardware."""
    for spec in RESOURCE_SPECS:
        if spec["hardware"] in available_hardware:
            mcp.resource(spec["uri"])(spec["impl"])

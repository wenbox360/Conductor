# tools.py

from fastmcp import FastMCP, Context
from typing import Dict, Any
from sendQueue import add_command_to_queue, wait_for_response

def register_tools(mcp: FastMCP):
    """Register all tools with the MCP server."""
    
    @mcp.tool
    async def piezo_beep(context: Context, duration: int = 500) -> Dict[str, Any]:
        """Control piezo buzzer - frequency in Hz, duration in milliseconds."""
        command = {
            "type": "WRITE",
            "command": 2,  # Buzzer command ID
            "duration": duration
        }
        add_command_to_queue(command)
        return {"message": f"Queued beep for {duration}ms"}
    
    @mcp.tool
    async def control_servo(context: Context, position: int) -> Dict[str, Any]:
        """Control servo motor position - position in degrees (0-180)."""
        # Validate input
        if not 0 <= position <= 180:
            return {"error": "Position must be between 0 and 180 degrees"}
        
        # Single servo command ID
        servo_command_id = 20
        
        command = {
            "type": "WRITE",
            "command": servo_command_id,
            "value": position
        }
        add_command_to_queue(command)
        
        return {
            "message": f"Servo set to {position} degrees",
            "position": position,
            "command_id": servo_command_id
        }
    

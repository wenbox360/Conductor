# resources.py

import uuid
import time
from fastmcp import FastMCP, Context
from sendQueue import add_command_to_queue, wait_for_response

def register_resources(mcp: FastMCP):
    """Register all resources with the MCP server."""
    
    @mcp.resource("sensor://ir/GP2Y0A21YK0F") 
    async def get_ir_sensor_reading(context: Context) -> str:
        """Get reading from IR sensor model."""
        
        # Generate unique response key for this specific request
        # This ensures each concurrent call gets its own response
        request_id = str(uuid.uuid4())[:8]  # Short unique ID
        response_key = f"ir_GP2Y0A21YK0F_{request_id}"
        
        # Add read command to queue
        command = {
            "type": "READ", 
            "command": 1,
            "response_key": response_key
        }
        add_command_to_queue(command)
        
        # Wait for response with timeout
        value = wait_for_response(response_key, timeout=2.0)
        
        # Format response for distance sensor
        return f"IR Sensor (GP2Y0A21YK0F) reads {value} cm (request: {request_id})"
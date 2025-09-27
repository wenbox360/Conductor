# hardware_cmd.py

"""
Hardware command utilities - now using sendQueue for actual communication.
This file provides convenience functions that wrap the queue system.
"""

from sendQueue import add_command_to_queue, wait_for_response
import uuid

def send_hardware_read_command(command: int) -> float:
    """Send a read command to hardware and return the sensor value."""
    # Generate unique response key
    response_key = f"read_cmd_{uuid.uuid4().hex[:8]}"
    
    cmd = {
        "type": "READ",
        "command": command,
        "response_key": response_key
    }
    
    add_command_to_queue(cmd)
    response = wait_for_response(response_key, timeout=2.0)
    
    try:
        return float(response)
    except (ValueError, TypeError):
        return 0.0

def send_hardware_write_command(command: int, value: int) -> bool:
    """Send a write command to hardware and return success status."""
    # Generate unique response key
    response_key = f"write_cmd_{uuid.uuid4().hex[:8]}"
    
    cmd = {
        "type": "WRITE", 
        "command": command,
        "value": value,
        "response_key": response_key
    }
    
    add_command_to_queue(cmd)
    response = wait_for_response(response_key, timeout=2.0)
    
    return "OK" in str(response).upper() or "SUCCESS" in str(response).upper()
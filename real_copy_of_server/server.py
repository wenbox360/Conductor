# server.py

from fastmcp import FastMCP
from resources import register_resources
from tools import register_tools
from prompts import register_prompts
from sendQueue import start_send_queue_processor
import json
import os
import threading
import time

def get_available_hardware() -> set[str]:
    """Get set of available hardware from mappings file."""
    try:
        # Use the same path as in setup_server()
        mappings_file = "../frontend-wjsons/registry-server/mappings.json"
        print(f"DEBUG: Looking for mappings file at: {os.path.abspath(mappings_file)}")
        
        if os.path.exists(mappings_file):
            print(f"DEBUG: Mappings file exists")
            with open(mappings_file, 'r') as f:
                mappings = json.load(f)
                print(f"DEBUG: Raw mappings data: {mappings}")
                
                hardware_parts = set()
                for mapping in mappings:
                    part_id = mapping.get('partId', '')
                    print(f"DEBUG: Found partId: '{part_id}'")
                    if part_id:
                        hardware_parts.add(part_id)
                        
                print(f"DEBUG: Final hardware_parts set: {hardware_parts}")
                return hardware_parts
        else:
            print(f"DEBUG: Mappings file does not exist at {os.path.abspath(mappings_file)}")
    except Exception as e:
        print(f"DEBUG: Error reading hardware mappings: {e}")
    
    print("DEBUG: Returning empty set")
    return set()


def watch_mappings_file(register_func, mappings_file):
    """Watch the mappings file for changes and reload tools when it changes."""
    last_modified = 0
    
    while True:
        try:
            if os.path.exists(mappings_file):
                current_modified = os.path.getmtime(mappings_file)
                if current_modified != last_modified:
                    if last_modified != 0:  # Skip initial load
                        print("Mappings file changed, reloading tools...")
                        register_func()
                    last_modified = current_modified
        except Exception as e:
            print(f"Error watching mappings file: {e}")
        
        time.sleep(1)  # Check every second

def setup_server() -> FastMCP:
    """Initializes and configures the MCP server instance."""
    print("Setting up MCP server...")
    mcp = FastMCP("MHacks 2025 MCP Server")
    
    # # Clear mappings on fresh start
    # mappings_file = "../frontend-wjsons/registry-server/mappings.json"
    # try:
    #     with open(mappings_file, 'w') as f:
    #         json.dump([], f)
    #     print("Cleared mappings on fresh start")
    # except Exception as e:
    #     print(f"Error clearing mappings: {e}")
    
    # Register static handlers first
    #register_resources(mcp)
    register_prompts(mcp)
    
    # Dynamic tool registration - will be updated when mappings change
    def register_dynamic_tools():
        print("DEBUG: register_dynamic_tools() called")
        available_hardware = get_available_hardware()
        print(f"DEBUG: Available hardware result: {available_hardware}")
        register_tools(mcp, available_hardware)
        print("DEBUG: register_tools() completed")
    
    # Initial tool registration
    register_dynamic_tools()
    
    # Start file watcher in background thread
    mappings_file = "../frontend-wjsons/registry-server/mappings.json"
    watcher_thread = threading.Thread(
        target=watch_mappings_file, 
        args=(register_dynamic_tools, mappings_file),
        daemon=True
    )
    watcher_thread.start()
    print("Started mappings file watcher...")
    
    start_send_queue_processor()
    
    return mcp

# Create the server object for FastMCP Cloud
mcp = setup_server()

if __name__ == "__main__":
    mcp.run()
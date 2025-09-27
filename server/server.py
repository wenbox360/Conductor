# server.py

from fastmcp import FastMCP
from resources import register_resources
from sendQueue import start_queue_processor

# --- Configuration ---
HOST = "127.0.0.1"  # Localhost
PORT = 8080         # Standard port for local development

def setup_server() -> FastMCP:
    """Initializes and configures the MCP server instance."""
    print("Setting up MCP server...")
    mcp = FastMCP()
    
    # Register all resource handlers (e.g., from resources.py)
    register_resources(mcp)
    print("All resources have been registered.")
    
    return mcp

def main():
    """Main function to set up and run the server."""
    # In a real application, this would start your hardware communication thread
    start_queue_processor()
    
    mcp_server = setup_server()
    
    print("\nStarting MCP server with STDIO transport")
    print("Press Ctrl+C to shut down.")
    
    try:
        # This call blocks and runs the server indefinitely using STDIO transport
        mcp_server.run()
    except KeyboardInterrupt:
        print("\nShutdown signal received. Closing server.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Server has been shut down.")

if __name__ == "__main__":
    main()
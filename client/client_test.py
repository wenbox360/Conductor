# client_test.py

import asyncio
from fastmcp import Client # Corrected import for MCPError

# --- Configuration ---
# This must match the server's host and port
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

async def main():
    """
    Connects to the FastMCP server over the network and reads a resource.
    """
    print(f"Attempting to connect to server at {SERVER_HOST}:{SERVER_PORT}...")

    try:
        # Initialize the client to connect to the server's network address
        client = Client(host=SERVER_HOST, port=SERVER_PORT)

        # 'async with' ensures the connection is properly opened and closed
        async with client:
            print("Connection successful. Ready to send requests.")
            
            # --- Test Case 1: A standard sensor model ---
            ir_model_to_test = "sharp_gp2y0a21yk"
            resource_uri = f"sensor://ir/{ir_model_to_test}"
            
            print(f"\nRequesting data from: {resource_uri}")
            response = await client.read_resource(resource_uri)
            
            print("--- Server Response ---")
            print(f"Data: {response.data}")
            print("-----------------------")

            # --- Test Case 2: A different sensor model ---
            ir_model_to_test_2 = "vl53l0x"
            resource_uri_2 = f"sensor://ir/{ir_model_to_test_2}"

            print(f"\nRequesting data from: {resource_uri_2}")
            response_2 = await client.read_resource(resource_uri_2)

            print("--- Server Response ---")
            print(f"Data: {response_2.data}")
            print("-----------------------")

    except ConnectionRefusedError:
        print("\n[ERROR] Connection refused.")
        print("Please make sure the server.py script is running in a separate terminal.")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
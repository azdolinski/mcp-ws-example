import sys
sys.dont_write_bytecode = True

import asyncio
import threading
import time
import os
from pathlib import Path

# Add the src directory to Python path
src_path = str(Path(__file__).parent / "src")
sys.path.insert(0, src_path)

from client import MCPClient

def run_server():
    """Run the weather server in a separate process"""
    os.system(f"python {Path(__file__).parent}/server.py")

async def run_client():
    """Run the weather client and make some test requests"""
    client = MCPClient()
    
    # Connect to the server
    server_path = str(Path(__file__).parent / "server.py")
    await client.connect_to_server(server_path)
    
    try:
        # Get detailed information about available tools
        response = await client.session.list_tools()
        print("\nAvailable tools:")
        for tool in response.tools:
            print(f"\nTool: {tool.name}")
            print(f"Description: {tool.description}")
            print(f"Input Schema: {tool.inputSchema}")

        # Test get-alerts for California
        print("\nTesting get-alerts for CA...")
        response = await client.session.call_tool("get-alerts", {"state": "CA"})
        print("Alerts response:", response.content)
        
        # Test get-forecast for San Francisco
        print("\nTesting get-forecast for San Francisco...")
        response = await client.session.call_tool(
            "get-forecast", 
            {"latitude": 37.7749, "longitude": -122.4194}
        )
        print("Forecast response:", response.content)
        
    finally:
        # Clean up
        await client.exit_stack.aclose()

async def main():
    # Start the server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True  # Thread will be terminated when main program exits
    server_thread.start()
    
    # Wait a bit for the server to start
    time.sleep(2)
    
    # Run the client
    await run_client()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import threading
import time
import sys
sys.dont_write_bytecode = True
from pathlib import Path

# Add the src directory to Python path
src_path = str(Path(__file__).parent / "src")
sys.path.insert(0, src_path)

from client_ws import WebSocketClient
import uvicorn
import subprocess

def run_server():
    """Run the weather server using uvicorn"""
    global server_process
    server_process = subprocess.Popen(["python", "server_ws.py"], cwd=Path(__file__).parent)
    return server_process

async def run_client():
    """Run the weather client and make test requests using WebSocket"""
    client = WebSocketClient("ws://localhost:8000/ws")
    
    try:
        # Connect to the server
        await client.connect()
        
        # Get detailed information about available tools
        response = await client.list_tools()
        print("\nAvailable tools:")
        for tool in response.tools:
            print(f"\nTool: {tool.name}")
            print(f"Description: {tool.description}")
            print(f"Input Schema: {tool.inputSchema}")

        # Test get-alerts for California
        print("\nTesting get-alerts for CA...")
        response = await client.call_tool("get-alerts", {"state": "CA"})
        print("Alerts response:", response.content)
        
        # Test get-forecast for San Francisco
        print("\nTesting get-forecast for San Francisco...")
        response = await client.call_tool(
            "get-forecast", 
            {"latitude": 37.7749, "longitude": -122.4194}
        )
        print("Forecast response:", response.content)
        
    finally:
        # Clean up
        await client.close()

async def main():
    """Main test function"""
    # Start the server in a separate process
    server_proc = run_server()
    
    try:
        # Wait a bit for the server to start
        await asyncio.sleep(2)
        
        # Run the client tests
        await run_client()
    finally:
        # Clean up the server process
        if server_proc.poll() is None:  # If process is still running
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
            except subprocess.TimeoutExpired:
                server_proc.kill()  # Force kill if it doesn't shut down gracefully
                server_proc.wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        # Extra cleanup in case the server process is still running
        if 'server_process' in globals() and server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()

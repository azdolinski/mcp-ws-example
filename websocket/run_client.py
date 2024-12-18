#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True

import asyncio
import argparse
from client_ws import WebSocketClient

async def run_client(ws_url: str):
    client = WebSocketClient(ws_url)
    
    try:
        # Connect to the server
        await client.connect()
        print("Connected to MCP Server successfully!")
        
        # List available tools
        response = await client.list_tools()
        print("\nAvailable tools:")
        for tool in response.tools:
            print(f"\nTool: {tool.name}")
            print(f"Description: {tool.description}")
            print(f"Input Schema: {tool.inputSchema}")

        while True:
            print("\nSelect a tool to use:")
            print("0. List available tools")
            print("1. get-alerts (requires state)")
            print("2. get-forecast (requires latitude and longitude)")
            print("3. Exit")
            
            choice = input("\nEnter your choice (0-3): ")
            
            if choice == "0":
                print("\nAvailable tools:")
                for tool in response.tools:
                    print(f"\nTool: {tool.name}")
                    print(f"Description: {tool.description}")
                    print(f"Input Schema: {tool.inputSchema}")
                
            elif choice == "1":
                state_input = input("Enter state code [CA]: ").upper()
                state = state_input if state_input else "CA"
                response = await client.call_tool("get-alerts", {"state": state})
                print("\nAlerts response:", response.content)
                
            elif choice == "2":
                lat_input = input("Enter latitude like 37.7749 for San Francisco [37.7749]: ")
                lat = float(lat_input) if lat_input else 37.7749
                lon_input = input("Enter longitude like -122.4194 for San Francisco [-122.4194]: ")
                lon = float(lon_input) if lon_input else -122.4194
                response = await client.call_tool(
                    "get-forecast", 
                    {"latitude": lat, "longitude": lon}
                )
                print("\nForecast response:", response.content)
                
            elif choice == "3":
                print("Exiting...")
                break
            
            else:
                print("Invalid choice. Please try again.")
                
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await client.close()

def main():
    parser = argparse.ArgumentParser(description='MCP WebSocket Client')
    parser.add_argument('--host', type=str, default='localhost',
                      help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=8000,
                      help='Server port (default: 8000)')
    
    args = parser.parse_args()
    
    ws_url = f"ws://{args.host}:{args.port}/ws"
    print(f"Connecting to MCP Server at {ws_url}")
    
    asyncio.run(run_client(ws_url))

if __name__ == "__main__":
    main()

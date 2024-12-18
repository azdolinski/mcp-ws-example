import asyncio
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from fastapi import FastAPI, WebSocket
from mcp.server import Server
from mcp.server.websocket import websocket_server
from mcp.types import Tool, TextContent
import uvicorn
import httpx
import json

# Add the src directory to Python path
src_path = str(Path(__file__).parent / "src")
sys.path.insert(0, src_path)

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

app = FastAPI()
weather_server = Server("weather")

async def make_nws_request(url: str) -> dict:
    """Make a request to the NWS API with proper error handling"""
    async with httpx.AsyncClient() as client:
        headers = {"User-Agent": USER_AGENT}
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

@weather_server.list_tools()
async def handle_list_tools():
    """Handler for listing available tools"""
    return [
        Tool(
            name="get-weather",
            description="Get the current weather for a location",
            inputSchema={
                "type": "object",
                "required": ["latitude", "longitude"],
                "properties": {
                    "latitude": {"type": "number", "description": "Latitude of the location"},
                    "longitude": {"type": "number", "description": "Longitude of the location"}
                }
            }
        ),
        Tool(
            name="get-alerts",
            description="Get active weather alerts for a US state",
            inputSchema={
                "type": "object",
                "required": ["state"],
                "properties": {
                    "state": {"type": "string", "description": "US state abbreviation"}
                }
            }
        ),
        Tool(
            name="get-forecast",
            description="Get weather forecast for a location",
            inputSchema={
                "type": "object",
                "required": ["latitude", "longitude"],
                "properties": {
                    "latitude": {"type": "number", "description": "Latitude of the location"},
                    "longitude": {"type": "number", "description": "Longitude of the location"}
                }
            }
        )
    ]

@weather_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Handler for calling tools"""
    if name == "get-weather":
        if not arguments or "latitude" not in arguments or "longitude" not in arguments:
            return [TextContent(type="text", text="Missing required arguments: latitude and longitude")]

        try:
            lat = float(arguments["latitude"])
            lon = float(arguments["longitude"])
            
            async with httpx.AsyncClient() as client:
                # First get the forecast grid endpoint
                points_url = f"{NWS_API_BASE}/points/{lat},{lon}"
                headers = {"User-Agent": USER_AGENT}
                
                response = await client.get(points_url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                forecast_url = data["properties"]["forecast"]
                
                # Now get the actual forecast
                response = await client.get(forecast_url, headers=headers)
                response.raise_for_status()
                
                forecast = response.json()
                current_period = forecast["properties"]["periods"][0]
                
                return [TextContent(
                    type="text",
                    text=f"Weather forecast for {current_period['name']}:\n"
                         f"Temperature: {current_period['temperature']}°{current_period['temperatureUnit']}\n"
                         f"Conditions: {current_period['shortForecast']}\n"
                         f"Wind: {current_period['windSpeed']} {current_period['windDirection']}"
                )]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting weather: {str(e)}")]
    
    elif name == "get-alerts":
        if not arguments or "state" not in arguments:
            return [TextContent(type="text", text="Missing required argument: state")]
        
        try:
            state = arguments["state"]
            url = f"{NWS_API_BASE}/alerts/active?area={state}"
            data = await make_nws_request(url)
            
            alerts = []
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                alerts.append({
                    "event": props.get("event"),
                    "area": props.get("areaDesc"),
                    "severity": props.get("severity"),
                    "status": props.get("status"),
                    "headline": props.get("headline")
                })
            
            return [TextContent(type="text", text=json.dumps(alerts, indent=2))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting alerts: {str(e)}")]
    
    elif name == "get-forecast":
        if not arguments or "latitude" not in arguments or "longitude" not in arguments:
            return [TextContent(type="text", text="Missing required arguments: latitude and longitude")]
        
        try:
            lat = float(arguments["latitude"])
            lon = float(arguments["longitude"])
            
            # First get the forecast grid endpoint
            points_url = f"{NWS_API_BASE}/points/{lat},{lon}"
            points_data = await make_nws_request(points_url)
            
            # Get the forecast URL from the points response
            forecast_url = points_data["properties"]["forecast"]
            forecast_data = await make_nws_request(forecast_url)
            
            # Extract relevant forecast information
            periods = forecast_data["properties"]["periods"]
            forecasts = [{
                "name": period["name"],
                "temperature": period["temperature"],
                "temperatureUnit": period["temperatureUnit"],
                "shortForecast": period["shortForecast"]
            } for period in periods]
            
            return [TextContent(type="text", text=json.dumps(forecasts, indent=2))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting forecast: {str(e)}")]
    
    else:
        return [TextContent(type="text", text="Unknown tool")]

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that handles client connections"""
    # Check if the client requested the MCP subprotocol
    if "mcp" not in websocket.scope.get("subprotocols", []):
        await websocket.close(1002)
        return
        
    async with websocket_server(websocket.scope, websocket.receive, websocket.send) as (read_stream, write_stream):
        await weather_server.run(read_stream, write_stream, weather_server.create_initialization_options())

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

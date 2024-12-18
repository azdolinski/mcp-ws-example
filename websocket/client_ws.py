import sys
sys.dont_write_bytecode = True

import asyncio
from typing import Optional
from contextlib import AsyncExitStack
import websockets
from mcp import ClientSession
from mcp.types import JSONRPCMessage
import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

class WebSocketClient:
    def __init__(self, url: str = "ws://localhost:8000/ws"):
        self.url = url
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.websocket = None
        
    async def connect(self):
        """Connect to the WebSocket server"""
        self.websocket = await websockets.connect(self.url, subprotocols=["mcp"])
        
        # Create memory streams for communication
        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)
        
        # Start WebSocket reader and writer tasks
        asyncio.create_task(self._ws_reader(read_stream_writer))
        asyncio.create_task(self._ws_writer(write_stream_reader))
        
        # Create client session
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self.session.initialize()
        
    async def _ws_reader(self, writer: MemoryObjectSendStream):
        """Read messages from WebSocket and forward them to the client session"""
        try:
            while True:
                message = await self.websocket.recv()
                try:
                    parsed = JSONRPCMessage.model_validate_json(message)
                    await writer.send(parsed)
                except Exception as exc:
                    await writer.send(exc)
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
            # Connection closed, clean up
            if not writer._closed:
                await writer.aclose()
        except Exception as e:
            print(f"Error in WebSocket reader: {str(e)}")
            if not writer._closed:
                await writer.aclose()
            
    async def _ws_writer(self, reader: MemoryObjectReceiveStream):
        """Read messages from memory stream and write to WebSocket"""
        try:
            async with reader:
                async for message in reader:
                    if self.websocket:
                        await self.websocket.send(message.model_dump_json())
        except Exception as e:
            print(f"Error in WebSocket writer: {str(e)}")
            if not reader._closed:
                await reader.aclose()
            
    async def close(self):
        """Close the connection and clean up resources"""
        try:
            if self.websocket:
                await self.websocket.close()
            await self.exit_stack.aclose()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            
    async def list_tools(self):
        """Get list of available tools from server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.list_tools()
    
    async def call_tool(self, tool_name: str, arguments: dict):
        """Call a specific tool on the server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.call_tool(tool_name, arguments)

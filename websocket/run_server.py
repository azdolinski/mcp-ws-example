#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True

import uvicorn
from server_ws import app
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run MCP WebSocket Server')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                      help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                      help='Port to bind to (default: 8000)')
    
    args = parser.parse_args()
    
    print(f"Starting MCP WebSocket Server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()

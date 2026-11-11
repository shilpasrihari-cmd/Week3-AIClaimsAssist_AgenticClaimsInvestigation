"""MCP stdio server exposing the Week 3 VIN decoder."""

from __future__ import annotations

import asyncio

from mcp.server import MCPServer

from vin_decoder import decode_vehicle_vin as decode_vehicle_vin_function


server = MCPServer("aiclaimsassist-vin")


@server.tool(name="decode_vehicle_vin")
def decode_vehicle_vin(vin: str) -> dict:
    """Decode a VIN using the existing NHTSA decoder."""
    return decode_vehicle_vin_function(vin)


if __name__ == "__main__":
    asyncio.run(server.run_stdio_async())

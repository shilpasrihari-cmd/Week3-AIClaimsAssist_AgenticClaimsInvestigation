from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
from textwrap import dedent

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
VIN = "1HGCM82633A004352"
SERVER_BOOTSTRAP = dedent(
    """
    import asyncio
    import json
    from unittest.mock import patch

    import vin_decoder
    from mcp_server import server

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return json.dumps({
                "Results": [{
                    "VIN": "1HGCM82633A004352",
                    "Manufacturer": "Honda",
                    "Model": "Accord",
                    "ModelYear": "2003",
                    "VehicleType": "PASSENGER CAR",
                    "ErrorCode": "0",
                }]
            }).encode("utf-8")

    async def main():
        with patch.object(vin_decoder, "urlopen", return_value=FakeResponse()):
            await server.run_stdio_async()

    asyncio.run(main())
    """
)


def _result_data(result) -> dict:
    if result.structured_content:
        return result.structured_content
    return json.loads(result.content[0].text)


async def _run_client_test() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-c", SERVER_BOOTSTRAP],
        cwd=ROOT,
        env=environment,
    )

    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            assert [tool.name for tool in tools.tools] == ["decode_vehicle_vin"]

            success = await session.call_tool("decode_vehicle_vin", {"vin": f"  {VIN.lower()}  "})
            decoded = _result_data(success)
            assert decoded["success"] is True
            assert decoded["vin"] == VIN
            assert decoded["manufacturer"] == "Honda"
            assert decoded["model"] == "Accord"
            assert decoded["model_year"] == 2003
            assert decoded["vehicle_type"] == "PASSENGER CAR"
            assert decoded["source_url"].startswith("https://vpic.nhtsa.dot.gov/")
            assert decoded["retrieval_timestamp"]

            invalid = await session.call_tool("decode_vehicle_vin", {"vin": "invalid"})
            invalid_data = _result_data(invalid)
            assert invalid_data["success"] is False
            assert invalid_data["error_type"] == "INVALID_VIN"


def test_mcp_client_connects_discovers_and_invokes_tool() -> None:
    asyncio.run(_run_client_test())

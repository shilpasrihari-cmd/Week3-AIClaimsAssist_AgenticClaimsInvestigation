from __future__ import annotations

import asyncio
from unittest.mock import patch

import mcp_server


def test_vin_decoder_tool_is_registered() -> None:
    tools = asyncio.run(mcp_server.server.list_tools())

    assert [tool.name for tool in tools] == ["decode_vehicle_vin"]


def test_mcp_tool_delegates_to_existing_decoder() -> None:
    expected = {"success": True, "vin": "TEST"}
    with patch.object(mcp_server, "decode_vehicle_vin_function", return_value=expected) as decoder:
        result = mcp_server.decode_vehicle_vin("TEST")

    decoder.assert_called_once_with("TEST")
    assert result == expected


def test_invalid_vin_result_is_returned_clearly() -> None:
    expected = {"success": False, "error_type": "INVALID_VIN"}
    with patch.object(mcp_server, "decode_vehicle_vin_function", return_value=expected):
        result = mcp_server.decode_vehicle_vin("invalid")

    assert result == expected


def test_mcp_tool_does_not_make_live_calls() -> None:
    expected = {"success": False, "error_type": "REQUEST_ERROR"}
    with patch.object(mcp_server, "decode_vehicle_vin_function", return_value=expected) as decoder:
        result = mcp_server.decode_vehicle_vin("1HGCM82633A004352")

    decoder.assert_called_once()
    assert result["error_type"] == "REQUEST_ERROR"

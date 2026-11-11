from __future__ import annotations

from urllib.error import HTTPError
from unittest.mock import patch

from vin_decoder import decode_vehicle_vin


VIN = "1HGCM82633A004352"


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return self.body


def test_valid_vin_is_normalized_and_decoded() -> None:
    body = b'{"Results":[{"VIN":"1HGCM82633A004352","Manufacturer":"Honda","Make":"Honda","Model":"Accord","ModelYear":"2003","VehicleType":"PASSENGER CAR","ErrorCode":"0"}]}'
    with patch("vin_decoder.urlopen", return_value=FakeResponse(body)) as mocked:
        result = decode_vehicle_vin(f"  {VIN.lower()}  ")

    assert result["success"] is True
    assert result["vin"] == VIN
    assert result["manufacturer"] == "Honda"
    assert result["model"] == "Accord"
    assert result["model_year"] == 2003
    assert result["vehicle_type"] == "PASSENGER CAR"
    request = mocked.call_args.args[0]
    assert request.full_url.endswith(f"/{VIN}?format=json")
    assert mocked.call_args.kwargs["timeout"] == 10


def test_invalid_vin_is_rejected_without_a_request() -> None:
    with patch("vin_decoder.urlopen") as mocked:
        result = decode_vehicle_vin("1HGCM82603IOQ4352")

    assert result["success"] is False
    assert result["error_type"] == "INVALID_VIN"
    mocked.assert_not_called()


def test_missing_decoded_fields_fail_without_inventing_values() -> None:
    body = b'{"Results":[{"Manufacturer":"Honda","Model":"","ModelYear":"2003","VehicleType":"PASSENGER CAR","ErrorCode":"0"}]}'
    with patch("vin_decoder.urlopen", return_value=FakeResponse(body)):
        result = decode_vehicle_vin(VIN)

    assert result["success"] is False
    assert result["error_type"] == "INCOMPLETE_RESPONSE"
    assert result["missing_fields"] == ["model"]
    assert result["model"] is None


def test_timeout_and_http_errors_return_clear_failures() -> None:
    with patch("vin_decoder.urlopen", side_effect=TimeoutError("timed out")):
        timeout_result = decode_vehicle_vin(VIN)
    with patch(
        "vin_decoder.urlopen",
        side_effect=HTTPError("https://example.test", 503, "unavailable", {}, None),
    ):
        http_result = decode_vehicle_vin(VIN)

    assert timeout_result["error_type"] == "REQUEST_ERROR"
    assert http_result["error_type"] == "HTTP_ERROR"


def test_malformed_response_returns_clear_failure() -> None:
    with patch("vin_decoder.urlopen", return_value=FakeResponse(b"not-json")):
        result = decode_vehicle_vin(VIN)

    assert result["success"] is False
    assert result["error_type"] == "MALFORMED_RESPONSE"

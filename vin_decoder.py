"""Small client for the public NHTSA vPIC VIN decoder."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


VPIC_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues"
VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def decode_vehicle_vin(vin: str) -> dict:
    """Decode a VIN and return normalized vehicle fields or a clear error."""
    normalized_vin = vin.strip().upper() if isinstance(vin, str) else ""
    if not VIN_PATTERN.fullmatch(normalized_vin):
        return {
            "success": False,
            "vin": normalized_vin,
            "manufacturer": None,
            "model": None,
            "model_year": None,
            "vehicle_type": None,
            "source_url": None,
            "retrieval_timestamp": None,
            "error_type": "INVALID_VIN",
            "error_message": "VIN must contain exactly 17 characters and cannot contain I, O or Q.",
        }

    source_url = f"{VPIC_URL}/{normalized_vin}?format=json"
    result = {
        "success": False,
        "vin": normalized_vin,
        "manufacturer": None,
        "model": None,
        "model_year": None,
        "vehicle_type": None,
        "source_url": source_url,
        "retrieval_timestamp": None,
    }
    request = Request(source_url, headers={"Accept": "application/json"})

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result["retrieval_timestamp"] = datetime.now(timezone.utc).isoformat()
    except HTTPError as exc:
        result.update(
            error_type="HTTP_ERROR",
            error_message=f"NHTSA returned HTTP {exc.code}.",
        )
        return result
    except (TimeoutError, URLError, OSError) as exc:
        result.update(
            error_type="REQUEST_ERROR",
            error_message=f"Unable to retrieve NHTSA VIN data: {exc}",
        )
        return result
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        result.update(
            error_type="MALFORMED_RESPONSE",
            error_message=f"NHTSA returned an unreadable response: {exc}",
        )
        return result

    rows = payload.get("Results") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        result.update(
            error_type="EMPTY_OR_AMBIGUOUS_RESPONSE",
            error_message="NHTSA did not return one unambiguous vehicle result.",
        )
        return result

    row = rows[0]
    if str(row.get("ErrorCode", "0")) not in {"", "0"}:
        result.update(
            error_type="API_RESPONSE_ERROR",
            error_message=str(row.get("ErrorText") or "NHTSA reported a VIN decoding error."),
        )
        return result

    manufacturer = row.get("Manufacturer") or row.get("Make")
    model = row.get("Model")
    model_year_value = row.get("ModelYear")
    vehicle_type = row.get("VehicleType")
    missing_fields = [
        name
        for name, value in (
            ("manufacturer", manufacturer),
            ("model", model),
            ("model_year", model_year_value),
            ("vehicle_type", vehicle_type),
        )
        if value in (None, "", "0")
    ]
    if missing_fields:
        result.update(
            error_type="INCOMPLETE_RESPONSE",
            error_message="NHTSA response is missing required vehicle fields.",
            missing_fields=missing_fields,
        )
        return result

    try:
        model_year = int(model_year_value)
    except (TypeError, ValueError):
        result.update(
            error_type="INCOMPLETE_RESPONSE",
            error_message="NHTSA returned an invalid model year.",
            missing_fields=["model_year"],
        )
        return result

    result.update(
        success=True,
        manufacturer=str(manufacturer),
        model=str(model),
        model_year=model_year,
        vehicle_type=str(vehicle_type),
    )
    return result


__all__ = ["decode_vehicle_vin"]

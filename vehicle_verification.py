"""Compare a claim's reported vehicle with a decoded VIN response."""

from __future__ import annotations

from claim_lookup import get_claim_details


def verify_claim_vehicle(claim_id: str, decoded_result: dict) -> dict:
    """Return a neutral vehicle verification result without changing the claim."""
    details = get_claim_details(claim_id)
    if not details["found"]:
        return {"found": False, "claim_id": claim_id}

    claim = details["claim"]
    reported = {
        "vin": claim.get("vin"),
        "make": claim.get("reported_make"),
        "model": claim.get("reported_model"),
        "year": claim.get("reported_year"),
    }
    decoded = {
        "vin": decoded_result.get("vin"),
        "manufacturer": decoded_result.get("manufacturer"),
        "model": decoded_result.get("model"),
        "year": decoded_result.get("model_year"),
    }
    base_result = {
        "found": True,
        "claim_id": claim_id,
        "reported_vehicle": reported,
        "decoded_vehicle": decoded,
        "fields_that_match": [],
        "fields_that_differ": [],
    }

    if not decoded_result.get("success"):
        return {
            **base_result,
            "verification_status": "UNABLE_TO_VERIFY",
            "explanation": "The VIN decoder did not return a successful result; no comparison was completed.",
        }

    def normalized_text(value: object) -> str:
        return str(value).strip().casefold()

    if not normalized_text(decoded["vin"]) or normalized_text(decoded["vin"]) != normalized_text(reported["vin"]):
        return {
            **base_result,
            "verification_status": "UNABLE_TO_VERIFY",
            "explanation": "The decoded VIN does not correspond to the claim VIN, so vehicle comparison was not completed.",
        }

    missing_fields = [
        field
        for field, value in (
            ("make", decoded["manufacturer"]),
            ("model", decoded["model"]),
            ("year", decoded["year"]),
        )
        if value is None or str(value).strip() in {"", "0"}
    ]
    if missing_fields:
        return {
            **base_result,
            "verification_status": "UNABLE_TO_VERIFY",
            "explanation": "The decoded VIN response is incomplete, so vehicle comparison was not completed.",
        }

    comparisons = {
        "make": (reported["make"], decoded["manufacturer"]),
        "model": (reported["model"], decoded["model"]),
        "year": (reported["year"], decoded["year"]),
    }
    matches = []
    differs = []
    for field, (reported_value, decoded_value) in comparisons.items():
        if normalized_text(reported_value) == normalized_text(decoded_value):
            matches.append(field)
        else:
            differs.append(field)

    if differs:
        return {
            **base_result,
            "verification_status": "MISMATCH",
            "fields_that_match": matches,
            "fields_that_differ": differs,
            "explanation": "One or more reported vehicle fields differ from the reliable decoded response; this is not proof of fraud.",
        }

    return {
        **base_result,
        "verification_status": "MATCHED",
        "fields_that_match": matches,
        "explanation": "The reported make, model and year match the decoded VIN response.",
    }


__all__ = ["verify_claim_vehicle"]

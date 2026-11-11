from __future__ import annotations

import json
from pathlib import Path

import pytest

from vehicle_verification import verify_claim_vehicle


MATCHED_DECODER_RESULT = {
    "success": True,
    "vin": "SYNTHETICVIN00001",
    "manufacturer": "  peugeot ",
    "model": "208",
    "model_year": "2016",
}


def test_matching_vehicle_details_are_normalized() -> None:
    result = verify_claim_vehicle("CLM-MOT-0003", MATCHED_DECODER_RESULT)

    assert result["verification_status"] == "MATCHED"
    assert result["fields_that_match"] == ["make", "model", "year"]
    assert result["fields_that_differ"] == []


@pytest.mark.parametrize(
    ("field", "value"),
    [("manufacturer", "DifferentMake"), ("model", "DifferentModel"), ("model_year", 2020)],
)
def test_material_vehicle_differences_return_mismatch(field: str, value: object) -> None:
    decoded = dict(MATCHED_DECODER_RESULT)
    decoded[field] = value

    result = verify_claim_vehicle("CLM-MOT-0003", decoded)

    assert result["verification_status"] == "MISMATCH"
    assert result["fields_that_differ"] == [{"manufacturer": "make", "model": "model", "model_year": "year"}[field]]


def test_missing_fields_and_decoder_failure_cannot_be_verified() -> None:
    incomplete = dict(MATCHED_DECODER_RESULT)
    incomplete["model"] = ""
    failed = {"success": False, "error_type": "REQUEST_ERROR"}

    incomplete_result = verify_claim_vehicle("CLM-MOT-0003", incomplete)
    failed_result = verify_claim_vehicle("CLM-MOT-0003", failed)

    assert incomplete_result["verification_status"] == "UNABLE_TO_VERIFY"
    assert failed_result["verification_status"] == "UNABLE_TO_VERIFY"


def test_vin_mismatch_cannot_be_verified() -> None:
    decoded = dict(MATCHED_DECODER_RESULT)
    decoded["vin"] = "SYNTHETICVIN99999"

    result = verify_claim_vehicle("CLM-MOT-0003", decoded)

    assert result["verification_status"] == "UNABLE_TO_VERIFY"


def test_unknown_claim_returns_not_found() -> None:
    assert verify_claim_vehicle("CLM-UNKNOWN-9999", MATCHED_DECODER_RESULT) == {
        "found": False,
        "claim_id": "CLM-UNKNOWN-9999",
    }


def test_claim_data_is_not_modified() -> None:
    dataset_path = Path("data/claims/claims_dataset.json")
    before = json.loads(dataset_path.read_text(encoding="utf-8"))

    verify_claim_vehicle("CLM-MOT-0003", MATCHED_DECODER_RESULT)

    after = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert after == before

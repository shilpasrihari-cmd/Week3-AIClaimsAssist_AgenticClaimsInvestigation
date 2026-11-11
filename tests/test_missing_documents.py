from __future__ import annotations

import json
from pathlib import Path

import claim_lookup
import missing_documents
from missing_documents import get_missing_documents


def test_fnol_does_not_require_investigation_stage_documents() -> None:
    result = get_missing_documents("CLM-MOT-0001")

    missing_types = {
        item["document_type"] for item in result["missing_required_documents"]
    }
    assert "INVESTIGATION_SUMMARY" not in missing_types
    assert "VEHICLE_PHOTOGRAPHS" not in missing_types


def test_investigation_claim_identifies_required_and_conditional_documents() -> None:
    result = get_missing_documents("CLM-MOT-0005")

    required_types = {
        item["document_type"] for item in result["missing_required_documents"]
    }
    conditional_types = {
        item["document_type"]
        for item in result["missing_applicable_conditional_documents"]
    }
    assert "INVESTIGATION_SUMMARY" in required_types
    assert "VEHICLE_PHOTOGRAPHS" in conditional_types
    assert "POLICE_REPORT" not in conditional_types


def test_received_and_accepted_documents_satisfy_requirements(tmp_path, monkeypatch) -> None:
    source = Path("data/claims/claims_dataset.json")
    data = json.loads(source.read_text(encoding="utf-8"))
    for document in data["claim_documents"]:
        if document["claim_id"] == "CLM-MOT-0003":
            if document["document_type"] == "LOSS_NOTIFICATION":
                document["document_status"] = "RECEIVED"
            elif document["document_type"] == "VEHICLE_PHOTOGRAPHS":
                document["document_status"] = "ACCEPTED"
            elif document["document_type"] == "REPAIR_ESTIMATE":
                document["document_status"] = "PENDING"
    fixture = tmp_path / "claims.json"
    fixture.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(claim_lookup, "DATASET_PATH", fixture)

    result = get_missing_documents("CLM-MOT-0003")

    satisfied_types = {
        item["document_type"] for item in result["satisfied_requirements"]
    }
    missing_types = {
        item["document_type"]
        for item in result["missing_applicable_conditional_documents"]
    }
    assert "LOSS_NOTIFICATION" in satisfied_types
    assert "VEHICLE_PHOTOGRAPHS" in satisfied_types
    assert "REPAIR_ESTIMATE" in missing_types


def test_rejected_and_pending_documents_do_not_satisfy_requirements(tmp_path, monkeypatch) -> None:
    source = Path("data/claims/claims_dataset.json")
    data = json.loads(source.read_text(encoding="utf-8"))
    for document in data["claim_documents"]:
        if document["claim_id"] == "CLM-MOT-0006" and document["document_type"] == "POLICE_REPORT":
            document["document_status"] = "REJECTED"
    fixture = tmp_path / "claims.json"
    fixture.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(claim_lookup, "DATASET_PATH", fixture)

    result = get_missing_documents("CLM-MOT-0006")

    missing_types = {
        item["document_type"]
        for item in result["missing_applicable_conditional_documents"]
    }
    assert "POLICE_REPORT" in missing_types


def test_jurisdiction_specific_requirements_do_not_cross_apply() -> None:
    us_result = get_missing_documents("CLM-AUTO-US-0004")
    ontario_result = get_missing_documents("CLM-AUTO-CA-0003")
    us_types = {
        item["document_type"]
        for item in us_result["missing_applicable_conditional_documents"]
    }
    ontario_types = {
        item["document_type"]
        for item in ontario_result["missing_applicable_conditional_documents"]
    }
    assert "NY_NO_FAULT_NOTICE" in us_types
    assert "ONTARIO_ACCIDENT_BENEFITS_FORM" in ontario_types
    assert "ONTARIO_ACCIDENT_BENEFITS_FORM" not in us_types
    assert "NY_NO_FAULT_NOTICE" not in ontario_types


def test_unknown_claim_returns_not_found() -> None:
    assert get_missing_documents("CLM-UNKNOWN-9999") == {
        "found": False,
        "claim_id": "CLM-UNKNOWN-9999",
    }

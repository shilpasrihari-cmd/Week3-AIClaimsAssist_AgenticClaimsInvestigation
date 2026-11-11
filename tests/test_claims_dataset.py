from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from policy_loader import load_policy_documents


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "claims" / "claims_dataset.json"
REGISTRY_PATH = ROOT / "data" / "policy_registry.json"
EXPECTED_POLICIES = {"MOT-0000002", "MOT-0000004", "AUTO-US-0001", "AUTO-CA-0001"}
EXPECTED_VEHICLES = {
    "MOT-0000002": ("VEH-MOT-0000002", "SYNTHETICVIN00001", "Peugeot", "208", 2016),
    "MOT-0000004": ("VEH-MOT-0000004", "SYNTHETICVIN00002", "Opel", "Astra", 2008),
    "AUTO-US-0001": ("VEH-AUTO-US-0001", "SYNTHETICVIN00003", "Northstar", "Sedan", 2022),
    "AUTO-CA-0001": ("VEH-AUTO-CA-0001", "SYNTHETICVIN00004", "Mapleline", "Utility SUV", 2021),
}
STATUSES = {"FNOL", "OPEN", "UNDER_INVESTIGATION", "PENDING_REVIEW", "CLOSED"}


def _dataset() -> dict:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def _registry() -> dict[str, dict]:
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {item["policy_id"]: item for item in value["policies"]}


def test_dataset_has_exact_distribution_and_loader_smoke() -> None:
    data = _dataset()
    claims = data["claims"]
    assert len(claims) == 20
    assert sum(claim["insurance_type"] == "MOTOR" for claim in claims) == 10
    assert sum(claim["insurance_type"] == "AUTO" for claim in claims) == 10
    assert {claim["claim_status"] for claim in claims} == STATUSES
    for status in STATUSES:
        assert sum(claim["claim_status"] == status and claim["insurance_type"] == "MOTOR" for claim in claims) == 2
        assert sum(claim["claim_status"] == status and claim["insurance_type"] == "AUTO" for claim in claims) == 2
    assert len(load_policy_documents(ROOT)) == 18


def test_claim_policy_and_vehicle_metadata_match_registry_and_schedules() -> None:
    data = _dataset()
    registry = _registry()
    assert set(registry) == EXPECTED_POLICIES
    for claim in data["claims"]:
        policy = registry[claim["policy_id"]]
        jurisdiction = policy["jurisdiction"]["country"]
        if policy["jurisdiction"].get("subdivision"):
            jurisdiction += "-" + policy["jurisdiction"]["subdivision"]
        assert claim["policy_id"] in EXPECTED_POLICIES
        assert claim["insurance_type"] == policy["insurance_type"]
        assert claim["insurance_market"] == policy["insurance_market"]
        assert claim["jurisdiction"] == jurisdiction
        assert claim["currency"] == policy["currency"]
        assert tuple((claim[field] for field in ("vehicle_id", "vin", "reported_make", "reported_model", "reported_year"))) == EXPECTED_VEHICLES[claim["policy_id"]]


def test_ids_notes_documents_and_evidence_are_referentially_valid() -> None:
    data = _dataset()
    claims = {claim["claim_id"]: claim for claim in data["claims"]}
    note_ids = {note["note_id"] for note in data["claim_notes"]}
    document_ids = {document["document_id"] for document in data["claim_documents"]}
    assert len(claims) == 20
    assert len(note_ids) == len(data["claim_notes"])
    assert len(document_ids) == len(data["claim_documents"])
    assert len({item["evidence_id"] for item in data["evidence_observations"]}) == len(data["evidence_observations"])
    for note in data["claim_notes"]:
        assert note["claim_id"] in claims
    for document in data["claim_documents"]:
        assert document["claim_id"] in claims
        if document["source_reference"] is not None:
            assert (ROOT / document["source_reference"]).is_file()
    for observation in data["evidence_observations"]:
        assert observation["claim_id"] in claims
        assert set(observation["supporting_source_ids"]).issubset(note_ids | document_ids)


def test_dates_outcomes_and_timelines_are_consistent() -> None:
    data = _dataset()
    registry = _registry()
    for claim in data["claims"]:
        loss_date = datetime.fromisoformat(claim["loss_date"])
        reported_date = datetime.fromisoformat(claim["reported_date"])
        policy = registry[claim["policy_id"]]
        assert loss_date <= reported_date
        assert datetime.fromisoformat(policy["effective_date"]) <= loss_date <= datetime.fromisoformat(policy["expiration_date"])
        assert claim["claim_status"] in STATUSES
        assert claim["claim_outcome"] is None if claim["claim_status"] != "CLOSED" else claim["claim_outcome"] in {"SETTLED", "DENIED", "WITHDRAWN"}
    claim_dates = {claim["claim_id"]: datetime.fromisoformat(claim["reported_date"]) for claim in data["claims"]}
    for note in data["claim_notes"]:
        assert datetime.fromisoformat(note["note_timestamp"].replace("Z", "+00:00")).date() >= claim_dates[note["claim_id"]].date()


def test_vin_fixture_expectations_are_separate_from_actual_status() -> None:
    data = _dataset()
    expected_statuses = {claim["vehicle_verification"]["fixture"]["expected_status"] for claim in data["claims"]}
    assert expected_statuses == {"PENDING", "MATCHED", "MISMATCH", "UNABLE_TO_VERIFY"}
    assert all(claim["vehicle_verification"]["actual_status"] == "PENDING" for claim in data["claims"])
    assert data["external_api_calls"] is False


def test_no_fraud_scores_or_personal_information_fields() -> None:
    data = _dataset()
    assert data["fraud_scoring_implemented"] is False
    serialized = json.dumps(data).lower()
    assert "fraud_score" not in serialized
    assert "risk_score" not in serialized
    forbidden_keys = {"full_name", "email", "phone", "claimant_name", "policyholder_name", "home_address"}
    for collection in ("claims", "claim_notes", "claim_documents", "evidence_observations"):
        for record in data[collection]:
            assert forbidden_keys.isdisjoint(record)

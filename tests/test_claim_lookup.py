from __future__ import annotations

import json
from pathlib import Path

from claim_lookup import get_claim_details


def test_get_claim_details_returns_claim_metadata() -> None:
    result = get_claim_details("CLM-MOT-0005")

    assert result["found"] is True
    assert result["claim"]["policy_id"] == "MOT-0000002"
    assert result["claim"]["jurisdiction"] == "IT"
    assert result["claim"]["currency"] == "EUR"
    assert result["claim"]["claim_status"] == "UNDER_INVESTIGATION"


def test_get_claim_details_returns_related_records() -> None:
    result = get_claim_details("CLM-MOT-0005")

    assert all(note["claim_id"] == "CLM-MOT-0005" for note in result["claim_notes"])
    assert all(
        document["claim_id"] == "CLM-MOT-0005"
        for document in result["claim_documents"]
    )
    assert all(
        observation["claim_id"] == "CLM-MOT-0005"
        for observation in result["evidence_observations"]
    )
    assert result["claim_notes"]
    assert result["claim_documents"]
    assert result["evidence_observations"]


def test_get_claim_details_returns_not_found_for_unknown_claim() -> None:
    dataset_path = Path("data/claims/claims_dataset.json")
    dataset_before = json.loads(dataset_path.read_text(encoding="utf-8"))

    result = get_claim_details("CLM-UNKNOWN-9999")

    assert result == {"found": False, "claim_id": "CLM-UNKNOWN-9999"}
    dataset_after = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert dataset_after == dataset_before

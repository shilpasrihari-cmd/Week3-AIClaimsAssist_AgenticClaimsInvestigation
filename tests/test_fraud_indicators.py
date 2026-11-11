from __future__ import annotations

import json
from pathlib import Path

from fraud_indicators import evaluate_fraud_indicators


def test_confirmed_discrepancy_is_returned_with_original_sources() -> None:
    result = evaluate_fraud_indicators("CLM-MOT-0007")

    assert len(result["confirmed_discrepancies"]) == 1
    observation = result["confirmed_discrepancies"][0]
    assert observation["indicator_type"] == "DAMAGE_DESCRIPTION_CONFLICT"
    assert observation["verification_status"] == "CONFIRMED"
    assert observation["supporting_source_ids"] == [
        "NOTE-CLM-MOT-0007-02",
        "NOTE-CLM-MOT-0007-03",
    ]
    assert observation["review_required"] is True


def test_unverified_and_incomplete_observations_are_separated() -> None:
    unverified = evaluate_fraud_indicators("CLM-MOT-0005")
    incomplete = evaluate_fraud_indicators("CLM-MOT-0006")

    assert len(unverified["unverified_observations"]) == 1
    assert unverified["incomplete_evidence"] == []
    assert len(incomplete["incomplete_evidence"]) == 1
    assert incomplete["unverified_observations"] == []


def test_disproved_indicator_is_separated() -> None:
    result = evaluate_fraud_indicators("CLM-AUTO-CA-0005")

    assert len(result["disproved_indicators"]) == 1
    assert result["disproved_indicators"][0]["verification_status"] == "DISPROVED"
    assert result["disproved_indicators"][0]["review_required"] is False


def test_no_observations_returns_neutral_result() -> None:
    result = evaluate_fraud_indicators("CLM-MOT-0001")

    assert result["summary"] == "No evidence observations are recorded for this claim."
    assert result["confirmed_discrepancies"] == []
    assert result["unverified_observations"] == []
    assert result["incomplete_evidence"] == []
    assert result["disproved_indicators"] == []


def test_unknown_claim_returns_not_found() -> None:
    assert evaluate_fraud_indicators("CLM-UNKNOWN-9999") == {
        "found": False,
        "claim_id": "CLM-UNKNOWN-9999",
    }


def test_no_score_or_invented_sources_are_returned() -> None:
    result = evaluate_fraud_indicators("CLM-AUTO-CA-0004")
    dataset = json.loads(
        Path("data/claims/claims_dataset.json").read_text(encoding="utf-8")
    )
    source_ids = {
        source_id
        for observation in dataset["evidence_observations"]
        if observation["claim_id"] == "CLM-AUTO-CA-0004"
        for source_id in observation["supporting_source_ids"]
    }
    returned_sources = {
        source_id
        for group in (
            "confirmed_discrepancies",
            "unverified_observations",
            "incomplete_evidence",
            "disproved_indicators",
        )
        for observation in result[group]
        for source_id in observation["supporting_source_ids"]
    }
    assert "fraud_score" not in result
    assert returned_sources == source_ids

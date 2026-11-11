from __future__ import annotations

import json
from pathlib import Path

import fraud_risk
from fraud_risk import calculate_fraud_risk


def test_confirmed_indicator_contributes_configured_points() -> None:
    result = calculate_fraud_risk("CLM-MOT-0007")

    assert result["risk_score"] == 25
    assert result["score_breakdown"] == [
        {
            "evidence_id": "EVID-CLM-MOT-0007-01",
            "indicator_type": "DAMAGE_DESCRIPTION_CONFLICT",
            "points": 25,
        }
    ]
    assert result["human_review_required"] is True


def test_non_confirmed_indicators_contribute_zero() -> None:
    for claim_id in ("CLM-MOT-0005", "CLM-MOT-0006", "CLM-AUTO-CA-0005"):
        result = calculate_fraud_risk(claim_id)
        assert result["risk_score"] == 0
        assert result["score_breakdown"] == []


def test_claim_without_indicators_has_zero_score() -> None:
    result = calculate_fraud_risk("CLM-MOT-0001")

    assert result["risk_score"] == 0
    assert result["human_review_required"] is False


def test_multiple_confirmed_indicators_are_combined(monkeypatch) -> None:
    monkeypatch.setattr(
        fraud_risk,
        "evaluate_fraud_indicators",
        lambda claim_id: {
            "found": True,
            "claim_id": claim_id,
            "confirmed_discrepancies": [
                {
                    "evidence_id": "EVID-1",
                    "indicator_type": "DATE_INCONSISTENCY",
                    "review_required": True,
                },
                {
                    "evidence_id": "EVID-2",
                    "indicator_type": "VEHICLE_INFORMATION_DISCREPANCY",
                    "review_required": True,
                },
            ],
            "unverified_observations": [],
            "incomplete_evidence": [],
            "disproved_indicators": [],
        },
    )

    result = calculate_fraud_risk("CLM-TEST-1")

    assert result["risk_score"] == 35
    assert [item["points"] for item in result["score_breakdown"]] == [15, 20]


def test_score_is_capped_at_100(monkeypatch) -> None:
    confirmed = [
        {
            "evidence_id": f"EVID-{index}",
            "indicator_type": "DAMAGE_DESCRIPTION_CONFLICT",
            "review_required": True,
        }
        for index in range(5)
    ]
    monkeypatch.setattr(
        fraud_risk,
        "evaluate_fraud_indicators",
        lambda claim_id: {
            "found": True,
            "claim_id": claim_id,
            "confirmed_discrepancies": confirmed,
            "unverified_observations": [],
            "incomplete_evidence": [],
            "disproved_indicators": [],
        },
    )

    assert calculate_fraud_risk("CLM-TEST-2")["risk_score"] == 100


def test_unknown_claim_returns_not_found() -> None:
    assert calculate_fraud_risk("CLM-UNKNOWN-9999") == {
        "found": False,
        "claim_id": "CLM-UNKNOWN-9999",
    }


def test_scoring_does_not_modify_claim_records() -> None:
    dataset_path = Path("data/claims/claims_dataset.json")
    before = json.loads(dataset_path.read_text(encoding="utf-8"))

    calculate_fraud_risk("CLM-MOT-0007")

    after = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert after == before

"""Deterministic synthetic investigation-priority scoring."""

from __future__ import annotations

from fraud_indicators import evaluate_fraud_indicators


INDICATOR_WEIGHTS = {
    "DATE_INCONSISTENCY": 15,
    "VEHICLE_INFORMATION_DISCREPANCY": 20,
    "DAMAGE_DESCRIPTION_CONFLICT": 25,
    "CONTRADICTORY_NOTE": 15,
    "DUPLICATE_OR_RELATED_CLAIM": 20,
    "DOCUMENT_INCONSISTENCY": 15,
}


def calculate_fraud_risk(claim_id: str) -> dict:
    """Calculate a capped synthetic risk-priority score from confirmed evidence."""
    findings = evaluate_fraud_indicators(claim_id)
    if not findings["found"]:
        return {"found": False, "claim_id": claim_id}

    confirmed = findings["confirmed_discrepancies"]
    score_breakdown = [
        {
            "evidence_id": observation["evidence_id"],
            "indicator_type": observation["indicator_type"],
            "points": INDICATOR_WEIGHTS.get(observation["indicator_type"], 0),
        }
        for observation in confirmed
    ]
    raw_score = sum(item["points"] for item in score_breakdown)
    score = min(raw_score, 100)

    all_observations = [
        *findings["confirmed_discrepancies"],
        *findings["unverified_observations"],
        *findings["incomplete_evidence"],
        *findings["disproved_indicators"],
    ]
    human_review_required = any(
        observation["review_required"] for observation in all_observations
    )

    return {
        "found": True,
        "claim_id": claim_id,
        "risk_score": score,
        "score_breakdown": score_breakdown,
        "explanation": (
            "This is a synthetic investigation-priority indicator based only on "
            "supported confirmed discrepancies. It is not a fraud probability, "
            "proof of fraud, or a basis for automatic claim decisions."
        ),
        "human_review_required": human_review_required,
    }

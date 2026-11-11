"""Read-only organization of synthetic claim evidence observations."""

from __future__ import annotations

from claim_lookup import get_claim_details


def _observation_view(observation: dict) -> dict:
    return {
        "evidence_id": observation["evidence_id"],
        "indicator_type": observation["indicator_type"],
        "description": observation["indicator_description"],
        "verification_status": observation["verification_status"],
        "supporting_source_ids": observation["supporting_source_ids"],
        "review_required": observation["review_required"],
    }


def evaluate_fraud_indicators(claim_id: str) -> dict:
    """Organize existing evidence observations without calculating a score."""
    details = get_claim_details(claim_id)
    if not details["found"]:
        return {"found": False, "claim_id": claim_id}

    observations = details["evidence_observations"]
    grouped = {
        "CONFIRMED": [],
        "UNVERIFIED": [],
        "INCOMPLETE_DATA": [],
        "DISPROVED": [],
    }
    for observation in observations:
        status = observation["verification_status"]
        grouped.setdefault(status, []).append(_observation_view(observation))

    if not observations:
        summary = "No evidence observations are recorded for this claim."
    else:
        summary = (
            f"{len(observations)} evidence observation(s) are recorded. "
            "The findings require human review and are not a fraud conclusion."
        )

    return {
        "found": True,
        "claim_id": claim_id,
        "summary": summary,
        "confirmed_discrepancies": grouped["CONFIRMED"],
        "unverified_observations": grouped["UNVERIFIED"],
        "incomplete_evidence": grouped["INCOMPLETE_DATA"],
        "disproved_indicators": grouped["DISPROVED"],
    }

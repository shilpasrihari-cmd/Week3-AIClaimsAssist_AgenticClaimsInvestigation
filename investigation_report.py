"""Build a structured investigation report from existing workflow state."""

from __future__ import annotations

from typing import Any


def build_investigation_report(state: dict[str, Any]) -> dict[str, Any]:
    """Format existing investigation results without rerunning any tools."""
    claim_id = state.get("claim_id")
    if not state.get("found", False) or "claim_details" not in state:
        return {
            "found": False,
            "claim_id": claim_id,
            "error": state.get("error", f"Claim not found: {claim_id}"),
        }

    details = state["claim_details"]
    claim = details["claim"]
    notes = sorted(
        details.get("claim_notes", []),
        key=lambda note: note.get("note_timestamp", ""),
    )
    indicators = state.get("fraud_indicators", {})
    missing = state.get("missing_documents", {})
    risk = state.get("fraud_risk", {})

    summary = (
        f"{claim['claim_id']} records a {claim['loss_type']} loss "
        f"reported on {claim['loss_date']} at {claim['loss_location']}."
    )

    return {
        "found": True,
        "claim_id": claim["claim_id"],
        "fraud_risk_score": {
            "risk_score": risk.get("risk_score"),
            "score_breakdown": risk.get("score_breakdown", []),
            "explanation": risk.get("explanation"),
        },
        "fraud_description": {
            "confirmed_discrepancies": indicators.get(
                "confirmed_discrepancies", []
            ),
            "unverified_observations": indicators.get(
                "unverified_observations", []
            ),
            "incomplete_evidence": indicators.get("incomplete_evidence", []),
            "disproved_indicators": indicators.get("disproved_indicators", []),
            "summary": indicators.get("summary"),
        },
        "missing_documents": {
            "missing_required_documents": missing.get(
                "missing_required_documents", []
            ),
            "missing_applicable_conditional_documents": missing.get(
                "missing_applicable_conditional_documents", []
            ),
            "satisfied_requirements": missing.get("satisfied_requirements", []),
        },
        "claim_summary_and_notes": {
            "claim_id": claim["claim_id"],
            "policy_id": claim["policy_id"],
            "claim_status": claim["claim_status"],
            "loss_type": claim["loss_type"],
            "loss_date": claim["loss_date"],
            "loss_location": claim["loss_location"],
            "claimed_amount": claim["claimed_amount"],
            "summary": summary,
            "claim_notes": notes,
        },
        "supporting_information": {
            "vehicle_verification": state.get("vehicle_verification"),
            "policy_citations": state.get("policy_citations", []),
        },
        "human_review_status": state.get("review_status", "PENDING_REVIEW"),
    }


__all__ = ["build_investigation_report"]

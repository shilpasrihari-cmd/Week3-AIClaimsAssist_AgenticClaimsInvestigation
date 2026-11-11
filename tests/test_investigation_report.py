from __future__ import annotations

import copy

from investigation_report import build_investigation_report


def _state() -> dict:
    return {
        "found": True,
        "claim_id": "CLM-TEST-0001",
        "claim_details": {
            "claim": {
                "claim_id": "CLM-TEST-0001",
                "policy_id": "AUTO-US-0001",
                "claim_status": "UNDER_INVESTIGATION",
                "loss_type": "collision",
                "loss_date": "2025-01-02",
                "loss_location": "Albany, NY",
                "claimed_amount": 1200,
            },
            "claim_notes": [
                {"note_id": "N2", "note_timestamp": "2025-01-04T10:00:00Z"},
                {"note_id": "N1", "note_timestamp": "2025-01-03T10:00:00Z"},
            ],
        },
        "missing_documents": {
            "missing_required_documents": [{"document_type": "LOSS_NOTIFICATION"}],
            "missing_applicable_conditional_documents": [
                {"document_type": "REPAIR_ESTIMATE", "reason": "damage review"}
            ],
            "satisfied_requirements": [],
        },
        "fraud_indicators": {
            "confirmed_discrepancies": [
                {
                    "description": "Date differs",
                    "supporting_source_ids": ["N1"],
                    "review_required": True,
                }
            ],
            "unverified_observations": [],
            "incomplete_evidence": [],
            "disproved_indicators": [],
            "summary": "Review required.",
        },
        "fraud_risk": {
            "risk_score": 15,
            "score_breakdown": [{"evidence_id": "E1", "points": 15}],
            "explanation": "Synthetic priority score, not a fraud probability.",
        },
        "vehicle_verification": {"verification_status": "MATCHED"},
        "policy_citations": [{"source_reference": "AUTO-US-0001/contract"}],
        "review_status": "ACCEPTED_FOR_REPORTING",
    }


def test_report_contains_sections_and_preserves_values() -> None:
    state = _state()
    report = build_investigation_report(state)

    assert set(
        [
            "fraud_risk_score",
            "fraud_description",
            "missing_documents",
            "claim_summary_and_notes",
        ]
    ).issubset(report)
    assert report["fraud_risk_score"]["risk_score"] == 15
    assert report["fraud_risk_score"]["score_breakdown"] == state["fraud_risk"]["score_breakdown"]
    assert report["fraud_description"]["confirmed_discrepancies"] == state["fraud_indicators"]["confirmed_discrepancies"]
    assert report["supporting_information"]["policy_citations"] == state["policy_citations"]
    assert report["human_review_status"] == "ACCEPTED_FOR_REPORTING"


def test_report_categorizes_documents_and_sorts_notes() -> None:
    report = build_investigation_report(_state())

    assert report["missing_documents"]["missing_required_documents"]
    assert report["missing_documents"]["missing_applicable_conditional_documents"]
    notes = report["claim_summary_and_notes"]["claim_notes"]
    assert [note["note_id"] for note in notes] == ["N1", "N2"]


def test_report_does_not_rerun_tools_or_mutate_state() -> None:
    state = _state()
    before = copy.deepcopy(state)

    report = build_investigation_report(state)

    assert report["found"] is True
    assert state == before


def test_unknown_state_returns_no_fabricated_report() -> None:
    result = build_investigation_report(
        {"found": False, "claim_id": "CLM-UNKNOWN", "error": "not found"}
    )

    assert result == {
        "found": False,
        "claim_id": "CLM-UNKNOWN",
        "error": "not found",
    }

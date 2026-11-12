"""Minimal Streamlit dashboard for the claims workflow."""

from __future__ import annotations

import json
import base64
from pathlib import Path
import uuid

import streamlit as st

from claims_agent import investigate_claim, resume_investigation
from investigation_report import build_investigation_report


ROOT = Path(__file__).resolve().parent
CLAIMS_PATH = ROOT / "data" / "claims" / "claims_dataset.json"
BACKGROUND_PATH = ROOT / "assets" / "claims_background.svg"


def _claim_ids() -> list[str]:
    data = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    return [claim["claim_id"] for claim in data["claims"]]


def _clear_investigation() -> None:
    for key in ("investigation_state", "investigation_report", "thread_id"):
        st.session_state.pop(key, None)


def _format_location(location: object) -> str:
    if not isinstance(location, dict):
        return str(location) if location is not None else "Unavailable"

    parts = [
        location.get("city"),
        location.get("jurisdiction"),
        location.get("country_or_market"),
    ]
    return ", ".join(str(part) for part in parts if part) or "Unavailable"


def _display_value(value: object) -> str:
    """Keep summary-table columns Arrow-compatible across mixed source types."""
    return "Unavailable" if value is None else str(value)


def _apply_page_style() -> None:
    image_data = base64.b64encode(BACKGROUND_PATH.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(7, 14, 24, 0.76), rgba(7, 14, 24, 0.86)),
                url('data:image/svg+xml;base64,{image_data}');
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        [data-testid="stSidebar"] {{
            background-color: rgba(8, 17, 29, 0.92);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _show_report(report: dict, state: dict) -> None:
    if not report.get("found"):
        st.error(report.get("error", "The claim could not be found."))
        return

    fraud_tab, documents_tab, report_tab = st.tabs(
        ["Fraud", "Missing documents", "Report"]
    )
    risk = report["fraud_risk_score"]
    with fraud_tab:
        score = risk.get("risk_score")
        fraud = report["fraud_description"]
        fraud_summary = fraud.get("summary", "No evidence summary is available.")
        review_status = report.get("human_review_status", "PENDING_REVIEW")
        st.table(
            [
                {"Fraud detail": "Fraud Score", "Value": _display_value(score)},
                {"Fraud detail": "Fraud Description", "Value": _display_value(fraud_summary)},
                {"Fraud detail": "Human Review", "Value": _display_value(review_status)},
                {
                    "Fraud detail": "Score Explanation",
                    "Value": "Based only on supported confirmed discrepancies; not a fraud probability or claim decision.",
                },
            ],
            alt="Fraud investigation summary",
        )
        breakdown = [
            {
                "Evidence ID": item.get("evidence_id"),
                "Indicator": item.get("indicator_type"),
                "Points": item.get("points"),
            }
            for item in risk.get("score_breakdown", [])
        ]
        if breakdown:
            st.table(breakdown, alt="Confirmed indicator score breakdown")
        else:
            st.caption("No supported confirmed discrepancies contributed points.")

        st.subheader("Evidence details")
        for heading, key in (
            ("Confirmed discrepancies", "confirmed_discrepancies"),
            ("Unverified observations", "unverified_observations"),
            ("Incomplete evidence", "incomplete_evidence"),
            ("Disproved indicators", "disproved_indicators"),
        ):
            st.markdown(f"**{heading}**")
            observations = fraud.get(key, [])
            if not observations:
                st.caption("None recorded.")
                continue
            observation_rows = [
                {
                    "Indicator": observation.get("indicator_type", "Observation"),
                    "Description": observation.get("description", "No description available."),
                    "Verification status": observation.get("verification_status", "Unknown"),
                    "Supporting sources": ", ".join(observation.get("supporting_source_ids", [])) or "None recorded",
                    "Human review": "Required" if observation.get("review_required") else "Not flagged",
                }
                for observation in observations
            ]
            st.table(observation_rows, alt=heading)

    with documents_tab:
        st.subheader("Missing documents")
        documents = report["missing_documents"]
        for heading, key in (
            ("Missing required documents", "missing_required_documents"),
            ("Missing applicable conditional documents", "missing_applicable_conditional_documents"),
        ):
            st.markdown(f"**{heading}**")
            missing_rows = [
                {"Document": item.get("document_type"), "Reason": item.get("reason")}
                for item in documents.get(key, [])
            ]
            if missing_rows:
                st.table(missing_rows, alt=heading)
            else:
                st.caption("None recorded.")
        with st.expander("Satisfied document requirements"):
            satisfied_rows = [
                {
                    "Document": item.get("document_type"),
                    "Document IDs": ", ".join(item.get("document_ids", [])),
                }
                for item in documents.get("satisfied_requirements", [])
            ]
            if satisfied_rows:
                st.table(satisfied_rows, alt="Satisfied document requirements")
            else:
                st.caption("None recorded.")

    with report_tab:
        st.subheader("Claim summary and notes")
        claim_summary = report["claim_summary_and_notes"]
        formatted_location = _format_location(claim_summary.get("loss_location"))
        formatted_summary = (
            f"{claim_summary.get('claim_id')} records a "
            f"{claim_summary.get('loss_type')} loss reported on "
            f"{claim_summary.get('loss_date')} at {formatted_location}."
        )
        claim_rows = [
            {
                "Field": label,
                "Value": (
                    formatted_location
                    if field == "loss_location"
                    else formatted_summary
                    if field == "summary"
                    else _display_value(claim_summary.get(field))
                ),
            }
            for label, field in (
                ("Claim ID", "claim_id"),
                ("Policy ID", "policy_id"),
                ("Claim status", "claim_status"),
                ("Loss type", "loss_type"),
                ("Loss date", "loss_date"),
                ("Loss location", "loss_location"),
                ("Claimed amount", "claimed_amount"),
                ("Summary", "summary"),
            )
        ]
        st.table(claim_rows, alt="Claim summary details")
        st.markdown("**Chronological claim notes**")
        notes = claim_summary.get("claim_notes", [])
        notes_container = st.expander(f"View claim notes ({len(notes)})")
        if notes:
            for note in notes:
                notes_container.markdown(
                    f"- **{note.get('note_timestamp', 'Unknown time')}** — "
                    f"{note.get('author_role', 'Unknown author')} / "
                    f"{note.get('note_type', 'Note')}: {note.get('note_text', '')}"
                )
        else:
            st.caption("No claim notes recorded.")

        supporting = report["supporting_information"]
        vehicle = supporting.get("vehicle_verification") or {}
        vehicle_status = vehicle.get("verification_status", "UNABLE_TO_VERIFY")
        with st.expander(f"Supporting information · Vehicle: {vehicle_status}"):
            reported_vehicle = vehicle.get("reported_vehicle") or {}
            decoded_vehicle = vehicle.get("decoded_vehicle") or {}
            vehicle_rows = [
                {"Field": "Verification status", "Value": _display_value(vehicle_status)},
                {"Field": "Reported VIN", "Value": _display_value(reported_vehicle.get("vin"))},
                {"Field": "Reported make", "Value": _display_value(reported_vehicle.get("make"))},
                {"Field": "Reported model", "Value": _display_value(reported_vehicle.get("model"))},
                {"Field": "Reported year", "Value": _display_value(reported_vehicle.get("year"))},
                {"Field": "Decoded VIN", "Value": _display_value(decoded_vehicle.get("vin"))},
                {"Field": "Decoded manufacturer", "Value": _display_value(decoded_vehicle.get("manufacturer"))},
                {"Field": "Decoded model", "Value": _display_value(decoded_vehicle.get("model"))},
                {"Field": "Decoded year", "Value": _display_value(decoded_vehicle.get("year"))},
                {"Field": "Matching fields", "Value": _display_value(", ".join(vehicle.get("fields_that_match", [])) or "None")},
                {"Field": "Different fields", "Value": _display_value(", ".join(vehicle.get("fields_that_differ", [])) or "None")},
            ]
            st.dataframe(vehicle_rows, hide_index=True, width="stretch")

        citation_rows = [
            {
                "Document": citation.get("source_filename", citation.get("document_id")),
                "Section": citation.get("section_heading"),
                "Source reference": citation.get("source_reference"),
                "Chunk ID": citation.get("chunk_id"),
            }
            for citation in supporting.get("policy_citations", [])
        ]
        citation_container = st.expander(f"Policy citations ({len(citation_rows)})")
        if citation_rows:
            citation_container.table(citation_rows)
        else:
            citation_container.caption("No policy citations returned.")

        st.subheader("Investigation review")
        review_status = report.get("human_review_status", "PENDING_REVIEW")
        st.table(
            [
                {"Review item": "Current status", "Value": review_status},
                {
                    "Review item": "Purpose",
                    "Value": "Human review is required before the investigation report is finalized.",
                },
                {
                    "Review item": "Decision scope",
                    "Value": "Findings are advisory and do not approve, deny or settle the claim.",
                },
            ],
            alt="Investigation review status",
        )

        paused = bool(state.get("__interrupt__")) and "review_status" not in state
        if paused:
            review_choice = st.radio(
                "Review decision",
                [
                    "Reviewed — Accept findings for reporting",
                    "Request more information — Further investigation required",
                ],
                key="review_decision",
            )
            if st.button("Submit review decision", key="submit_review_decision"):
                response = (
                    "ACCEPT_REPORT"
                    if review_choice.startswith("Reviewed")
                    else "REQUEST_MORE_INFO"
                )
                try:
                    resumed_state = resume_investigation(
                        st.session_state["thread_id"], response
                    )
                    st.session_state["investigation_state"] = resumed_state
                    st.session_state["investigation_report"] = build_investigation_report(
                        resumed_state
                    )
                    st.rerun()
                except Exception as error:
                    st.error(f"Review update failed: {type(error).__name__}")

def main() -> None:
    st.set_page_config(page_title="AIClaimsAssist", layout="wide")
    _apply_page_style()
    st.title("AIClaimsAssist — Agentic Claims Investigation Assistant")
    claim_ids = _claim_ids()
    with st.sidebar:
        st.header("Investigation setup")
        st.caption("Select a claim or policy record to investigate.")
        selected_claim_id = st.selectbox("Select a claim", claim_ids)
        run_investigation = st.button("Run Investigation", type="primary", width="stretch")

    if st.session_state.get("selected_claim_id") != selected_claim_id:
        _clear_investigation()
        st.session_state["selected_claim_id"] = selected_claim_id

    if run_investigation:
        _clear_investigation()
        thread_id = f"streamlit-{uuid.uuid4().hex}"
        try:
            state = investigate_claim(selected_claim_id, thread_id)
            st.session_state["thread_id"] = thread_id
            st.session_state["investigation_state"] = state
            st.session_state["investigation_report"] = build_investigation_report(state)
        except Exception as error:
            st.error(f"Investigation failed: {type(error).__name__}")

    state = st.session_state.get("investigation_state")
    report = st.session_state.get("investigation_report")
    if state is None or report is None:
        return

    _show_report(report, state)

if __name__ == "__main__":
    main()

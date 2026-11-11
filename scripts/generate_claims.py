"""Generate the deterministic Week 3 synthetic claim dataset."""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


SEED = 20261110
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "claims" / "claims_dataset.json"

POLICY_VEHICLES = {
    "MOT-0000002": {"vehicle_id": "VEH-MOT-0000002", "vin": "SYNTHETICVIN00001", "make": "Peugeot", "model": "208", "year": 2016, "market": "EU", "jurisdiction": "IT", "currency": "EUR", "insurance_type": "MOTOR"},
    "MOT-0000004": {"vehicle_id": "VEH-MOT-0000004", "vin": "SYNTHETICVIN00002", "make": "Opel", "model": "Astra", "year": 2008, "market": "EU", "jurisdiction": "IE", "currency": "EUR", "insurance_type": "MOTOR"},
    "AUTO-US-0001": {"vehicle_id": "VEH-AUTO-US-0001", "vin": "SYNTHETICVIN00003", "make": "Northstar", "model": "Sedan", "year": 2022, "market": "US", "jurisdiction": "US-NY", "currency": "USD", "insurance_type": "AUTO"},
    "AUTO-CA-0001": {"vehicle_id": "VEH-AUTO-CA-0001", "vin": "SYNTHETICVIN00004", "make": "Mapleline", "model": "Utility SUV", "year": 2021, "market": "Canada", "jurisdiction": "CA-ON", "currency": "CAD", "insurance_type": "AUTO"},
}

CLAIM_SPECS = [
    ("CLM-MOT-0001", "MOT-0000002", "FNOL", "vandalism", "2024-02-17", "Synthetic Milan", 2050.00, "Vehicle found with keyed door panel; photographs have not yet been received."),
    ("CLM-MOT-0002", "MOT-0000004", "FNOL", "theft", "2025-01-31", "Synthetic Dublin", 8200.00, "Vehicle reported missing from a fictional residential parking area."),
    ("CLM-MOT-0003", "MOT-0000002", "OPEN", "collision", "2024-03-29", "Synthetic Rome", 4750.00, "Rear bumper and boot damage reported after a low-speed collision."),
    ("CLM-MOT-0004", "MOT-0000004", "OPEN", "hail", "2025-03-11", "Synthetic Cork", 3150.00, "Small dents reported across the bonnet and roof after a synthetic storm event."),
    ("CLM-MOT-0005", "MOT-0000002", "UNDER_INVESTIGATION", "collision", "2024-05-12", "Synthetic Naples", 9600.00, "Rear-end impact reported; the first notice and later note contain different incident dates."),
    ("CLM-MOT-0006", "MOT-0000004", "UNDER_INVESTIGATION", "theft", "2025-04-07", "Synthetic Galway", 12400.00, "Vehicle theft reported; vehicle details in the intake note require comparison with the policy schedule."),
    ("CLM-MOT-0007", "MOT-0000002", "PENDING_REVIEW", "collision", "2024-08-21", "Synthetic Turin", 6800.00, "Photograph description and repair estimate describe different damaged panels."),
    ("CLM-MOT-0008", "MOT-0000004", "PENDING_REVIEW", "hail", "2025-08-30", "Synthetic Limerick", 4200.00, "Adjuster notes contain inconsistent descriptions of the reported damage extent."),
    ("CLM-MOT-0009", "MOT-0000002", "CLOSED", "vandalism", "2024-09-14", "Synthetic Florence", 1800.00, "Damage review completed with no supported discrepancy recorded."),
    ("CLM-MOT-0010", "MOT-0000004", "CLOSED", "collision", "2025-10-05", "Synthetic Waterford", 7350.00, "Closure review found an amount inconsistency between the inventory and final note."),
    ("CLM-AUTO-US-0001", "AUTO-US-0001", "FNOL", "collision", "2025-01-18", "Synthetic Albany", 6400.00, "Front corner impact reported at a fictional intersection; initial intake only."),
    ("CLM-AUTO-US-0002", "AUTO-US-0001", "OPEN", "weather", "2025-02-09", "Synthetic Buffalo", 2800.00, "Weather-related glass and roof damage reported; supporting photographs remain outstanding."),
    ("CLM-AUTO-US-0003", "AUTO-US-0001", "UNDER_INVESTIGATION", "theft", "2025-03-22", "Synthetic Rochester", 15800.00, "Theft report is being compared with another synthetic claim involving a similar vehicle location."),
    ("CLM-AUTO-US-0004", "AUTO-US-0001", "PENDING_REVIEW", "collision", "2025-04-16", "Synthetic Syracuse", 7100.00, "The local VIN fixture is expected to match the reported synthetic vehicle details."),
    ("CLM-AUTO-US-0005", "AUTO-US-0001", "CLOSED", "glass", "2025-06-03", "Synthetic Yonkers", 950.00, "Claim closed after review; the local VIN fixture is intentionally expected to differ in model year."),
    ("CLM-AUTO-CA-0001", "AUTO-CA-0001", "FNOL", "animal_strike", "2025-01-27", "Synthetic Toronto", 3900.00, "Front bumper damage reported after contact with an unidentified animal."),
    ("CLM-AUTO-CA-0002", "AUTO-CA-0001", "OPEN", "collision", "2025-02-14", "Synthetic Ottawa", 8600.00, "Intersection collision reported; third-party details are incomplete."),
    ("CLM-AUTO-CA-0003", "AUTO-CA-0001", "UNDER_INVESTIGATION", "collision", "2025-03-19", "Synthetic Hamilton", 11200.00, "Claimant statement and damage description conflict about the point of impact."),
    ("CLM-AUTO-CA-0004", "AUTO-CA-0001", "PENDING_REVIEW", "theft", "2025-04-28", "Synthetic London", 17600.00, "Police-report metadata and the intake record require a final consistency review."),
    ("CLM-AUTO-CA-0005", "AUTO-CA-0001", "CLOSED", "hail", "2025-07-12", "Synthetic Mississauga", 2950.00, "Claim closed after the apparent note contradiction was resolved as a wording error."),
]


def _timestamp(day: str, hour: int) -> str:
    return datetime.fromisoformat(f"{day}T{hour:02d}:00:00+00:00").isoformat().replace("+00:00", "Z")


def _claim_outcome(status: str) -> str | None:
    return {"CLOSED": "SETTLED"}.get(status)


def _fixture_expected(claim_id: str) -> dict:
    if claim_id in {"CLM-AUTO-US-0004", "CLM-AUTO-CA-0002"}:
        return {"fixture_id": "LOCAL-SYNTHETIC-MATCH-001", "expected_status": "MATCHED", "expected_decoded_fields": {"make": "Northstar" if "US" in claim_id else "Mapleline", "model_year": 2022 if "US" in claim_id else 2021}}
    if claim_id in {"CLM-MOT-0005", "CLM-AUTO-US-0005", "CLM-AUTO-CA-0003"}:
        return {"fixture_id": "LOCAL-SYNTHETIC-MISMATCH-001", "expected_status": "MISMATCH", "expected_decoded_fields": {"make": "FixtureMaker", "model": "DifferentModel", "model_year": 2020}}
    if claim_id in {"CLM-MOT-0001", "CLM-MOT-0002", "CLM-MOT-0006", "CLM-AUTO-CA-0004"}:
        return {"fixture_id": "LOCAL-SYNTHETIC-UNAVAILABLE-001", "expected_status": "UNABLE_TO_VERIFY", "expected_decoded_fields": None}
    return {"fixture_id": "LOCAL-SYNTHETIC-PENDING-001", "expected_status": "PENDING", "expected_decoded_fields": None}


def _notes(claim_id: str, status: str, loss_date: str, reported_date: str, description: str) -> list[dict]:
    special = {
        "CLM-MOT-0005": "The claimant first stated 2024-05-12, while a later contact note states 2024-05-13; both statements require human review.",
        "CLM-MOT-0006": "The intake note describes an Opel Astra, while the vehicle detail field is incomplete; no external VIN result exists.",
        "CLM-MOT-0007": "Photograph summary mentions rear-left damage, while the estimate mentions front-right damage.",
        "CLM-MOT-0008": "One note says roof-only hail dents; another says all body panels were affected.",
        "CLM-MOT-0010": "The document inventory amount is not supported by a separate physical source document; the closure amount remains for adjuster confirmation.",
        "CLM-AUTO-US-0003": "A potentially related synthetic claim has a similar loss location and vehicle description; relationship is unverified.",
        "CLM-AUTO-US-0005": "The local test fixture is expected to return a different model year; this is not an external verification result.",
        "CLM-AUTO-CA-0003": "The claimant describes front-left impact, while the adjuster note describes rear-right impact.",
        "CLM-AUTO-CA-0004": "The intake record and police-report reference use different fictional event-reference suffixes.",
        "CLM-AUTO-CA-0005": "An earlier note said hail was observed on the roof; the final review clarified that the note meant the vehicle was parked under cover.",
    }
    note_texts = [
        ("CLAIMANT", "FNOL", f"Synthetic claimant intake recorded on {reported_date}: {description}"),
        ("ADJUSTER", "DOCUMENT_REVIEW", "Adjuster opened the file and requested the applicable loss notification, vehicle photographs, repair estimate and any conditional police or witness material. No physical claim document is created by this dataset."),
    ]
    if status == "UNDER_INVESTIGATION":
        note_texts.append(("INVESTIGATOR", "INVESTIGATION", special.get(claim_id, "Investigation remains open while available claim facts are compared; no conclusion has been reached.")))
    elif status == "PENDING_REVIEW":
        note_texts.append(("SUPERVISOR", "ESCALATION", special.get(claim_id, "Investigation review is complete enough for human adjuster review; no automated decision is recorded.")))
    elif status == "CLOSED":
        note_texts.append(("ADJUSTER", "CLOSURE", special.get(claim_id, "Claim review completed and closed with no supported discrepancy recorded.")))
    else:
        note_texts.append(("SYSTEM", "CONTACT", "Claim remains in its current lifecycle status; outstanding evidence and document requirements are tracked separately."))
    result = []
    for index, (role, note_type, text) in enumerate(note_texts, start=1):
        day = date.fromisoformat(reported_date) + timedelta(days=index - 1)
        result.append({"note_id": f"NOTE-{claim_id}-{index:02d}", "claim_id": claim_id, "note_timestamp": _timestamp(day.isoformat(), 9 + index), "author_role": role, "note_type": note_type, "note_text": text})
    return result


def _documents(claim_id: str, status: str, loss_type: str) -> list[dict]:
    physical_loss = loss_type in {"collision", "vandalism", "hail", "weather", "glass", "animal_strike"}
    types = [
        ("LOSS_NOTIFICATION", "REQUIRED"),
        ("VEHICLE_PHOTOGRAPHS", "CONDITIONAL" if physical_loss else "NOT_APPLICABLE"),
        ("REPAIR_ESTIMATE", "CONDITIONAL" if physical_loss else "NOT_APPLICABLE"),
        ("POLICE_REPORT", "CONDITIONAL" if loss_type == "theft" else "NOT_APPLICABLE"),
        ("CLOSURE_LETTER", "REQUIRED" if status == "CLOSED" else "NOT_YET_REQUIRED"),
    ]
    records = []
    for index, (doc_type, requirement_state) in enumerate(types, start=1):
        status_value = "NOT_APPLICABLE" if requirement_state == "NOT_APPLICABLE" else "NOT_YET_REQUIRED" if requirement_state == "NOT_YET_REQUIRED" else "MISSING"
        records.append({"document_id": f"DOC-{claim_id}-{index:02d}", "claim_id": claim_id, "document_type": doc_type, "requirement_state": requirement_state, "document_status": status_value, "received_date": None, "source_reference": None})
    return records


def _evidence(claim_id: str, notes_by_claim: dict[str, list[dict]]) -> list[dict]:
    observations = {
        "CLM-MOT-0005": ("DATE_INCONSISTENCY", "Two chronological claim notes state different incident dates; the discrepancy is documented but not resolved.", "UNVERIFIED", True),
        "CLM-MOT-0006": ("VEHICLE_INFORMATION_DISCREPANCY", "The vehicle description in the intake note is incomplete relative to the policy vehicle fields.", "INCOMPLETE_DATA", True),
        "CLM-MOT-0007": ("DAMAGE_DESCRIPTION_CONFLICT", "The photograph summary and estimate describe different damaged vehicle areas.", "CONFIRMED", True),
        "CLM-MOT-0008": ("CONTRADICTORY_NOTE", "Two adjuster-facing notes describe different extents of hail damage.", "UNVERIFIED", True),
        "CLM-MOT-0010": ("DOCUMENT_INCONSISTENCY", "The closure note refers to an amount that is not supported by a separate physical claim document.", "INCOMPLETE_DATA", True),
        "CLM-AUTO-US-0003": ("DUPLICATE_OR_RELATED_CLAIM", "The notes identify a potentially related synthetic claim based on similar location and vehicle details; the relationship is unverified.", "UNVERIFIED", True),
        "CLM-AUTO-US-0005": ("VEHICLE_INFORMATION_DISCREPANCY", "A local test fixture is expected to decode a different model year; no external decoding result exists.", "UNVERIFIED", True),
        "CLM-AUTO-CA-0003": ("DAMAGE_DESCRIPTION_CONFLICT", "The claimant and adjuster notes describe different impact locations.", "CONFIRMED", True),
        "CLM-AUTO-CA-0004": ("DOCUMENT_INCONSISTENCY", "The intake and police-report reference values differ in their fictional suffixes.", "UNVERIFIED", True),
        "CLM-AUTO-CA-0005": ("CONTRADICTORY_NOTE", "An apparent contradiction was resolved as a wording error during review; it is recorded for auditability, not as a fraud conclusion.", "DISPROVED", False),
    }
    observation = observations.get(claim_id)
    if observation is None:
        return []
    kind, description, verification, review_required = observation
    note_ids = [note["note_id"] for note in notes_by_claim[claim_id][1:]]
    return [{"evidence_id": f"EVID-{claim_id}-01", "claim_id": claim_id, "indicator_type": kind, "indicator_description": description, "verification_status": verification, "supporting_source_ids": note_ids, "review_required": review_required}]


def build_dataset() -> dict:
    random.Random(SEED)  # Explicit fixed seed for reproducibility of this fixture set.
    claims = []
    notes = []
    documents = []
    by_claim_notes: dict[str, list[dict]] = {}
    for claim_id, policy_id, status, loss_type, loss_date, city, amount, description in CLAIM_SPECS:
        vehicle = POLICY_VEHICLES[policy_id]
        reported_date = (date.fromisoformat(loss_date) + timedelta(days=1 if status == "FNOL" else 2)).isoformat()
        claim = {
            "claim_id": claim_id,
            "policy_id": policy_id,
            "insurance_type": vehicle["insurance_type"],
            "insurance_market": vehicle["market"],
            "jurisdiction": vehicle["jurisdiction"],
            "currency": vehicle["currency"],
            "claim_status": status,
            "claim_outcome": _claim_outcome(status),
            "loss_type": loss_type,
            "loss_date": loss_date,
            "reported_date": reported_date,
            "loss_location": {"country_or_market": vehicle["jurisdiction"].split("-")[0], "jurisdiction": vehicle["jurisdiction"], "city": city, "location_type": "synthetic_public_location"},
            "loss_description": description,
            "claimed_amount": amount,
            "vehicle_id": vehicle["vehicle_id"],
            "vin": vehicle["vin"],
            "reported_make": vehicle["make"],
            "reported_model": vehicle["model"],
            "reported_year": vehicle["year"],
            "vehicle_verification": {"actual_status": "PENDING", "fixture": _fixture_expected(claim_id), "verification_note": "No external VIN API was called; fixture expectation is separate from actual verification status."},
        }
        claim_notes = _notes(claim_id, status, loss_date, reported_date, description)
        claims.append(claim)
        notes.extend(claim_notes)
        by_claim_notes[claim_id] = claim_notes
        documents.extend(_documents(claim_id, status, loss_type))
    evidence = [item for claim_id in by_claim_notes for item in _evidence(claim_id, by_claim_notes)]
    return {"schema_version": "1.0", "synthetic": True, "generation_seed": SEED, "external_api_calls": False, "fraud_scoring_implemented": False, "claims": claims, "claim_notes": notes, "claim_documents": documents, "evidence_observations": evidence}


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build_dataset(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")

"""Synthetic business rules for identifying missing claim documents."""

from __future__ import annotations

from claim_lookup import get_claim_details


ACTIVE_STATUSES = {"OPEN", "UNDER_INVESTIGATION", "PENDING_REVIEW", "CLOSED"}
VALID_DOCUMENT_STATUSES = {"RECEIVED", "ACCEPTED", "VERIFIED"}
DAMAGE_LOSS_TYPES = {"collision", "hail", "vandalism", "weather", "glass", "animal_strike"}


DOCUMENT_REQUIREMENTS = [
    {
        "document_type": "LOSS_NOTIFICATION",
        "insurance_types": {"MOTOR", "AUTO"},
        "loss_types": None,
        "jurisdictions": None,
        "statuses": {"FNOL", *ACTIVE_STATUSES},
        "kind": "REQUIRED",
        "reason": "The claim must have a recorded loss notification.",
    },
    {
        "document_type": "VEHICLE_PHOTOGRAPHS",
        "insurance_types": {"MOTOR", "AUTO"},
        "loss_types": DAMAGE_LOSS_TYPES,
        "jurisdictions": None,
        "statuses": ACTIVE_STATUSES,
        "kind": "CONDITIONAL",
        "reason": "Damage-related losses require photographs during claim review.",
    },
    {
        "document_type": "REPAIR_ESTIMATE",
        "insurance_types": {"MOTOR", "AUTO"},
        "loss_types": DAMAGE_LOSS_TYPES,
        "jurisdictions": None,
        "statuses": ACTIVE_STATUSES,
        "kind": "CONDITIONAL",
        "reason": "Damage-related losses require a repair estimate during claim review.",
    },
    {
        "document_type": "POLICE_REPORT",
        "insurance_types": {"MOTOR", "AUTO"},
        "loss_types": {"theft", "animal_strike"},
        "jurisdictions": None,
        "statuses": ACTIVE_STATUSES,
        "kind": "CONDITIONAL",
        "reason": "Theft or animal-strike losses require an incident report for review.",
    },
    {
        "document_type": "INVESTIGATION_SUMMARY",
        "insurance_types": {"MOTOR", "AUTO"},
        "loss_types": None,
        "jurisdictions": None,
        "statuses": {"UNDER_INVESTIGATION", "PENDING_REVIEW", "CLOSED"},
        "kind": "REQUIRED",
        "reason": "Investigation-stage claims require an investigation summary.",
    },
    {
        "document_type": "CLOSURE_LETTER",
        "insurance_types": {"MOTOR", "AUTO"},
        "loss_types": None,
        "jurisdictions": None,
        "statuses": {"CLOSED"},
        "kind": "REQUIRED",
        "reason": "Closed claims require a closure document.",
    },
    {
        "document_type": "NY_NO_FAULT_NOTICE",
        "insurance_types": {"AUTO"},
        "loss_types": {"collision"},
        "jurisdictions": {"US-NY"},
        "statuses": ACTIVE_STATUSES,
        "kind": "CONDITIONAL",
        "reason": "This configurable synthetic rule applies to collision claims in US-NY.",
    },
    {
        "document_type": "ONTARIO_ACCIDENT_BENEFITS_FORM",
        "insurance_types": {"AUTO"},
        "loss_types": {"collision"},
        "jurisdictions": {"CA-ON"},
        "statuses": ACTIVE_STATUSES,
        "kind": "CONDITIONAL",
        "reason": "This configurable synthetic rule applies to collision claims in CA-ON.",
    },
]


def get_missing_documents(claim_id: str) -> dict:
    """Return missing and satisfied document requirements for one claim."""
    details = get_claim_details(claim_id)
    if not details["found"]:
        return {"found": False, "claim_id": claim_id}

    claim = details["claim"]
    documents = details["claim_documents"]
    missing_required = []
    missing_conditional = []
    satisfied = []

    for requirement in DOCUMENT_REQUIREMENTS:
        if claim["insurance_type"] not in requirement["insurance_types"]:
            continue
        if requirement["jurisdictions"] and claim["jurisdiction"] not in requirement["jurisdictions"]:
            continue
        if requirement["loss_types"] and claim["loss_type"] not in requirement["loss_types"]:
            continue

        if claim["claim_status"] not in requirement["statuses"]:
            continue

        matching_documents = [
            document
            for document in documents
            if document["document_type"] == requirement["document_type"]
            and document["document_status"] in VALID_DOCUMENT_STATUSES
        ]
        if matching_documents:
            satisfied.append(
                {
                    "document_type": requirement["document_type"],
                    "document_ids": [item["document_id"] for item in matching_documents],
                }
            )
            continue

        missing_item = {
            "document_type": requirement["document_type"],
            "reason": requirement["reason"],
        }
        if requirement["kind"] == "REQUIRED":
            missing_required.append(missing_item)
        else:
            missing_conditional.append(missing_item)

    return {
        "found": True,
        "claim_id": claim_id,
        "claim_status": claim["claim_status"],
        "missing_required_documents": missing_required,
        "missing_applicable_conditional_documents": missing_conditional,
        "satisfied_requirements": satisfied,
    }

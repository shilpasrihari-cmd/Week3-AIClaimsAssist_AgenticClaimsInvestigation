"""Read-only lookup helpers for the synthetic claims dataset."""

from __future__ import annotations

import json
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parent / "data" / "claims" / "claims_dataset.json"


def get_claim_details(claim_id: str) -> dict:
    """Return one claim and its related records, or a not-found result."""
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    claim = next(
        (item for item in data["claims"] if item["claim_id"] == claim_id),
        None,
    )

    if claim is None:
        return {"found": False, "claim_id": claim_id}

    return {
        "found": True,
        "claim": claim,
        "claim_notes": [
            note for note in data["claim_notes"] if note["claim_id"] == claim_id
        ],
        "claim_documents": [
            document
            for document in data["claim_documents"]
            if document["claim_id"] == claim_id
        ],
        "evidence_observations": [
            observation
            for observation in data["evidence_observations"]
            if observation["claim_id"] == claim_id
        ],
    }

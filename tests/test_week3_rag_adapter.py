from __future__ import annotations

import hashlib
import json
from pathlib import Path

from policy_loader import load_policy_documents
from week3_rag_adapter import chunk_policy_documents


ROOT = Path(__file__).resolve().parents[1]


def test_both_strategies_chunk_all_18_approved_documents() -> None:
    documents = load_policy_documents(ROOT)
    expected_doc_ids = {document.doc_id for document in documents}

    fixed = chunk_policy_documents(ROOT, "fixed_size")
    section_aware = chunk_policy_documents(ROOT, "section_aware")

    assert {chunk.document_id for chunk in fixed} == expected_doc_ids
    assert {chunk.document_id for chunk in section_aware} == expected_doc_ids
    assert len(fixed) >= 18
    assert len(section_aware) >= 18
    assert all(chunk.text.strip() for chunk in fixed + section_aware)


def test_metadata_preserves_policy_and_auto_fields() -> None:
    chunks = chunk_policy_documents(ROOT, "section_aware")

    auto_us = next(chunk for chunk in chunks if chunk.policy_id == "AUTO-US-0001")
    auto_ca = next(chunk for chunk in chunks if chunk.policy_id == "AUTO-CA-0001")
    for chunk, jurisdiction, currency in (
        (auto_us, "US-NY", "USD"),
        (auto_ca, "CA-ON", "CAD"),
    ):
        assert chunk.metadata["policy_id"] == chunk.policy_id
        assert chunk.metadata["document_id"] == chunk.document_id
        assert chunk.metadata["jurisdiction"] == jurisdiction
        assert chunk.metadata["currency"] == currency
        assert chunk.metadata["insurance_type"] == "AUTO"
        assert chunk.metadata["source_reference"]


def test_chunk_ids_and_metadata_are_deterministic() -> None:
    first = chunk_policy_documents(ROOT, "fixed_size")
    second = chunk_policy_documents(ROOT, "fixed_size")

    first_values = [(chunk.chunk_id, chunk.text, chunk.metadata) for chunk in first]
    second_values = [(chunk.chunk_id, chunk.text, chunk.metadata) for chunk in second]
    assert first_values == second_values


def test_only_manifest_documents_are_included_and_files_are_unchanged() -> None:
    manifest_path = ROOT / "manifest.json"
    registry_path = ROOT / "data" / "policy_registry.json"
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (manifest_path, registry_path)
    }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_paths = {entry["path"] for entry in manifest["documents"]}

    chunks = chunk_policy_documents(ROOT, "section_aware")

    assert {chunk.metadata["source_reference"] for chunk in chunks} <= expected_paths
    after = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (manifest_path, registry_path)
    }
    assert after == before

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from policy_loader import PolicyLoaderError, load_policy_documents


WORKSPACE = Path(__file__).resolve().parents[1]


def test_week3_manifest_loads_exactly_18_documents() -> None:
    documents = load_policy_documents(WORKSPACE)

    assert len(documents) == 18
    assert all(document.extraction_succeeded for document in documents)
    assert {document.policy_id for document in documents} == {
        "MOT-0000002",
        "MOT-0000004",
        "AUTO-US-0001",
        "AUTO-CA-0001",
    }


def test_week3_metadata_and_policy_counts() -> None:
    documents = load_policy_documents(WORKSPACE)
    by_policy = {policy_id: sum(doc.policy_id == policy_id for doc in documents) for policy_id in {
        "MOT-0000002", "MOT-0000004", "AUTO-US-0001", "AUTO-CA-0001"
    }}

    assert by_policy == {
        "MOT-0000002": 4,
        "MOT-0000004": 4,
        "AUTO-US-0001": 5,
        "AUTO-CA-0001": 5,
    }
    assert all(doc.jurisdiction == "US-NY" and doc.currency == "USD" for doc in documents if doc.policy_id == "AUTO-US-0001")
    assert all(doc.jurisdiction == "CA-ON" and doc.currency == "CAD" for doc in documents if doc.policy_id == "AUTO-CA-0001")
    assert all(doc.jurisdiction in {"IT", "IE"} and doc.currency == "EUR" for doc in documents if doc.policy_id.startswith("MOT-"))


def _write_fixture(tmp_path: Path, entries: list[dict], policies: list[dict] | None = None) -> Path:
    (tmp_path / "data").mkdir()
    policy = {
        "policy_id": "AUTO-US-0001",
        "insurance_type": "AUTO",
        "insurance_market": "US",
        "jurisdiction": {"country": "US", "subdivision": "NY"},
        "currency": "USD",
        "document_references": [entry["path"] for entry in entries],
    }
    (tmp_path / "data" / "policy_registry.json").write_text(
        json.dumps({"policies": policies or [policy]}), encoding="utf-8"
    )
    (tmp_path / "manifest.json").write_text(json.dumps({"documents": entries}), encoding="utf-8")
    return tmp_path


def _entry(path: str = "fixture.md", **overrides: object) -> dict:
    result = {
        "doc_id": "DOC-FIXTURE",
        "policy_id": "AUTO-US-0001",
        "doc_type": "policy_contract",
        "format": "md",
        "path": path,
        "insurance_type": "AUTO",
        "insurance_market": "US",
        "jurisdiction": "US-NY",
        "currency": "USD",
    }
    result.update(overrides)
    return result


def test_unlisted_files_are_excluded(tmp_path: Path) -> None:
    (tmp_path / "fixture.md").write_text("listed", encoding="utf-8")
    (tmp_path / "unlisted.md").write_text("not listed", encoding="utf-8")
    docs = load_policy_documents(_write_fixture(tmp_path, [_entry()]))
    assert [doc.source_reference for doc in docs] == ["fixture.md"]


@pytest.mark.parametrize("bad_entry", [
    _entry(policy_id="UNKNOWN-0001"),
    _entry(jurisdiction="CA-ON"),
    _entry(currency="CAD"),
    _entry(path="../outside.md"),
    _entry(path="C:/outside.md"),
    _entry(path="fixture.txt", format="txt"),
])
def test_invalid_manifest_entries_are_rejected(tmp_path: Path, bad_entry: dict) -> None:
    (tmp_path / "fixture.md").write_text("listed", encoding="utf-8")
    with pytest.raises(PolicyLoaderError):
        load_policy_documents(_write_fixture(tmp_path, [bad_entry]))


def test_duplicate_document_ids_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "one.md").write_text("one", encoding="utf-8")
    (tmp_path / "two.md").write_text("two", encoding="utf-8")
    entries = [_entry(path="one.md"), _entry(path="two.md")]
    with pytest.raises(PolicyLoaderError, match="Duplicate document ID"):
        load_policy_documents(_write_fixture(tmp_path, entries))


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PolicyLoaderError, match="does not exist"):
        load_policy_documents(_write_fixture(tmp_path, [_entry(path="missing.md")]))


def test_unreadable_text_file_has_clear_error(tmp_path: Path) -> None:
    (tmp_path / "fixture.md").write_bytes(bytes([0xFF, 0xFE]))
    with pytest.raises(PolicyLoaderError, match="Unable to read document"):
        load_policy_documents(_write_fixture(tmp_path, [_entry()]))


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"outside-{tmp_path.name}"
    outside.mkdir()
    (outside / "fixture.md").write_text("outside", encoding="utf-8")
    link = tmp_path / "escape"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        if os.name != "nt":
            pytest.skip(f"symlink creation unavailable in this environment: {exc}")
        junction = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if junction.returncode != 0:
            pytest.skip(f"symlink and junction creation unavailable: {junction.stderr or junction.stdout}")
    with pytest.raises(PolicyLoaderError, match="escapes the workspace|different drive|does not exist"):
        load_policy_documents(_write_fixture(tmp_path, [_entry(path="escape/fixture.md")]))

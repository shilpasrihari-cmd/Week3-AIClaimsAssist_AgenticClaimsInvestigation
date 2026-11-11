"""Manifest-only loader for the Week 3 synthetic policy corpus.

This module deliberately does not scan directories.  The manifest is the
complete allow-list of documents, and every path is checked against both the
workspace boundary and the policy registry before extraction.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from Week2_AIClaimsAssist_RAG.ingestion.document_loader import extract_document


SUPPORTED_FORMATS = {".md", ".pdf", ".docx"}
ELIGIBLE_INSURANCE_TYPES = {"MOTOR", "AUTO"}


class PolicyLoaderError(ValueError):
    """Raised when the manifest or an approved policy document is invalid."""


@dataclass(frozen=True)
class PolicyDocument:
    """A successfully extracted policy document and validated policy metadata."""

    doc_id: str
    policy_id: str
    insurance_type: str
    insurance_market: str
    jurisdiction: str
    currency: str
    doc_type: str
    source_reference: str
    file_format: str
    extracted_text: str
    extraction_succeeded: bool = True


def _read_json(path: Path, description: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyLoaderError(f"Unable to read {description} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PolicyLoaderError(f"{description} must contain a JSON object: {path}")
    return value


def _normalise_relative_path(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/")).as_posix()


def _resolve_workspace_path(workspace_root: Path, source_reference: str) -> Path:
    if not isinstance(source_reference, str) or not source_reference.strip():
        raise PolicyLoaderError("Manifest document path must be a non-empty string")

    # Check both Windows and POSIX spellings because manifests are data and may
    # have been authored on a different host.
    if Path(source_reference).is_absolute() or PureWindowsPath(source_reference).is_absolute():
        raise PolicyLoaderError(f"Absolute manifest path is not allowed: {source_reference}")

    root = workspace_root.resolve()
    candidate = (root / Path(source_reference)).resolve()
    try:
        if os.path.commonpath((str(root), str(candidate))) != str(root):
            raise PolicyLoaderError(f"Manifest path escapes the workspace: {source_reference}")
    except ValueError as exc:
        raise PolicyLoaderError(f"Manifest path is on a different drive: {source_reference}") from exc

    if not candidate.is_file():
        raise PolicyLoaderError(f"Manifest document does not exist or is not a file: {source_reference}")
    return candidate


def _registry_jurisdiction(policy: dict[str, Any]) -> str:
    jurisdiction = policy.get("jurisdiction")
    if not isinstance(jurisdiction, dict):
        raise PolicyLoaderError(f"Registry jurisdiction is invalid for policy {policy.get('policy_id')}")
    country = jurisdiction.get("country")
    subdivision = jurisdiction.get("subdivision")
    if not isinstance(country, str) or not country:
        raise PolicyLoaderError(f"Registry country is missing for policy {policy.get('policy_id')}")
    return f"{country}-{subdivision}" if subdivision else country


def _load_registry(registry_path: Path) -> dict[str, dict[str, Any]]:
    registry = _read_json(registry_path, "policy registry")
    policies = registry.get("policies")
    if not isinstance(policies, list):
        raise PolicyLoaderError("Policy registry must contain a policies list")

    result: dict[str, dict[str, Any]] = {}
    for policy in policies:
        if not isinstance(policy, dict) or not isinstance(policy.get("policy_id"), str):
            raise PolicyLoaderError("Every registry policy must contain a string policy_id")
        policy_id = policy["policy_id"]
        if policy_id in result:
            raise PolicyLoaderError(f"Duplicate policy ID in registry: {policy_id}")
        if policy_id.startswith("COM-"):
            continue
        if policy.get("insurance_type") not in ELIGIBLE_INSURANCE_TYPES:
            continue
        result[policy_id] = policy
    return result


def _approved_references(policy: dict[str, Any]) -> set[str]:
    references = policy.get("document_references")
    if not isinstance(references, list) or not all(isinstance(item, str) for item in references):
        raise PolicyLoaderError(f"Registry document_references are invalid for policy {policy['policy_id']}")
    return {_normalise_relative_path(item) for item in references}


def _validate_entry(entry: Any, registry: dict[str, dict[str, Any]], workspace_root: Path) -> tuple[dict[str, Any], Path]:
    if not isinstance(entry, dict):
        raise PolicyLoaderError("Every manifest document entry must be an object")

    required = ("doc_id", "policy_id", "doc_type", "format", "path")
    missing = [field for field in required if not isinstance(entry.get(field), str) or not entry[field].strip()]
    if missing:
        raise PolicyLoaderError(f"Manifest document is missing required fields: {', '.join(missing)}")

    policy_id = entry["policy_id"]
    policy = registry.get(policy_id)
    if policy is None:
        raise PolicyLoaderError(f"Unknown or excluded policy ID: {policy_id}")

    source_reference = _normalise_relative_path(entry["path"])
    if source_reference not in _approved_references(policy):
        raise PolicyLoaderError(
            f"Document {entry['doc_id']} is not an approved registry reference for policy {policy_id}: {entry['path']}"
        )

    expected = {
        "insurance_type": policy.get("insurance_type"),
        "insurance_market": policy.get("insurance_market"),
        "jurisdiction": _registry_jurisdiction(policy),
        "currency": policy.get("currency"),
    }
    for field, expected_value in expected.items():
        if entry.get(field) != expected_value:
            raise PolicyLoaderError(
                f"Metadata mismatch for {entry['doc_id']} field {field}: "
                f"manifest={entry.get(field)!r}, registry={expected_value!r}"
            )

    file_path = _resolve_workspace_path(workspace_root, source_reference)
    if file_path.suffix.lower() not in SUPPORTED_FORMATS:
        raise PolicyLoaderError(f"Unsupported policy document type: {entry['path']}")
    return entry, file_path


def _extract(entry: dict[str, Any], file_path: Path) -> str:
    try:
        if file_path.suffix.lower() == ".md":
            text = file_path.read_text(encoding="utf-8")
        else:
            extraction = extract_document(file_path)
            if not extraction.extraction_succeeded:
                raise PolicyLoaderError(extraction.error or "text extraction failed")
            text = extraction.extracted_text
    except PolicyLoaderError:
        raise
    except (OSError, UnicodeError) as exc:
        raise PolicyLoaderError(f"Unable to read document {entry['path']}: {exc}") from exc
    if not text.strip():
        raise PolicyLoaderError(f"Document contains no extractable text: {entry['path']}")
    return text


def load_policy_documents(
    workspace_root: str | Path,
    manifest_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> list[PolicyDocument]:
    """Load exactly the policy documents listed by a validated manifest.

    No directory scanning occurs.  By default, all paths are resolved relative
    to *workspace_root*, and the default manifest/registry are the Week 3 files.
    """

    root = Path(workspace_root).resolve()
    manifest = Path(manifest_path) if manifest_path is not None else root / "manifest.json"
    registry = Path(registry_path) if registry_path is not None else root / "data" / "policy_registry.json"
    manifest_data = _read_json(manifest, "manifest")
    registry_by_id = _load_registry(registry)
    entries = manifest_data.get("documents")
    if not isinstance(entries, list):
        raise PolicyLoaderError("Manifest must contain a documents list")

    loaded: list[PolicyDocument] = []
    seen_ids: set[str] = set()
    for raw_entry in entries:
        entry, file_path = _validate_entry(raw_entry, registry_by_id, root)
        doc_id = entry["doc_id"]
        if doc_id in seen_ids:
            raise PolicyLoaderError(f"Duplicate document ID in manifest: {doc_id}")
        seen_ids.add(doc_id)
        loaded.append(
            PolicyDocument(
                doc_id=doc_id,
                policy_id=entry["policy_id"],
                insurance_type=entry["insurance_type"],
                insurance_market=entry["insurance_market"],
                jurisdiction=entry["jurisdiction"],
                currency=entry["currency"],
                doc_type=entry["doc_type"],
                source_reference=_normalise_relative_path(entry["path"]),
                file_format=file_path.suffix.lower().removeprefix("."),
                extracted_text=_extract(entry, file_path),
            )
        )
    return loaded


__all__ = ["PolicyDocument", "PolicyLoaderError", "load_policy_documents"]

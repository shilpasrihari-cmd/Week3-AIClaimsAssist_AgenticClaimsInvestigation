from __future__ import annotations

import json
from pathlib import Path

import pytest

from policy_search import search_policy


def test_search_finds_passages_for_both_auto_policies() -> None:
    us_results = search_policy("collision deductible", "AUTO-US-0001")
    ca_results = search_policy("collision deductible", "AUTO-CA-0001")

    assert us_results
    assert ca_results
    assert all(result["policy_id"] == "AUTO-US-0001" for result in us_results)
    assert all(result["policy_id"] == "AUTO-CA-0001" for result in ca_results)
    assert us_results[0]["currency"] == "USD"
    assert ca_results[0]["currency"] == "CAD"


@pytest.mark.parametrize("policy_id", ["MOT-0000002", "MOT-0000004"])
def test_search_finds_passages_for_each_motor_policy(policy_id: str) -> None:
    results = search_policy("coverage deductible", policy_id)

    assert results
    assert all(result["policy_id"] == policy_id for result in results)
    assert all(result["jurisdiction"] in {"IT", "IE"} for result in results)
    assert all(result["currency"] == "EUR" for result in results)


def test_cross_policy_passages_are_not_returned() -> None:
    results = search_policy("Ontario direct compensation property damage", "AUTO-US-0001")

    assert all(result["policy_id"] == "AUTO-US-0001" for result in results)


def test_unknown_or_excluded_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown or excluded policy ID"):
        search_policy("coverage", "COM-0000001")
    with pytest.raises(ValueError, match="Unknown or excluded policy ID"):
        search_policy("coverage", "AUTO-UNKNOWN-0001")


def test_empty_or_irrelevant_queries_return_no_results() -> None:
    assert search_policy("", "AUTO-US-0001") == []
    assert search_policy("zzzz-not-in-policy-text", "AUTO-US-0001") == []


def test_result_preserves_citation_metadata_and_only_manifest_sources() -> None:
    results = search_policy("uninsured motorist coverage", "AUTO-US-0001")
    manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
    manifest_paths = {entry["path"] for entry in manifest["documents"]}

    assert results
    for result in results:
        assert result["chunk_id"]
        assert result["document_id"]
        assert result["section_heading"]
        assert result["source_reference"] in manifest_paths
        assert result["jurisdiction"] == "US-NY"
        assert result["currency"] == "USD"
        assert result["text"].strip()

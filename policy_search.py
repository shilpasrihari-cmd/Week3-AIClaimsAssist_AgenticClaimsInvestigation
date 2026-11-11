"""Local BM25 search over the approved Week 3 policy chunks."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
WEEK2_ROOT = ROOT / "Week2_AIClaimsAssist_RAG"
if str(WEEK2_ROOT) not in sys.path:
    sys.path.insert(0, str(WEEK2_ROOT))


def _load_bm25_index_class():
    module_path = WEEK2_ROOT / "retrieval" / "bm25_retriever.py"
    spec = importlib.util.spec_from_file_location("week2_bm25_retriever", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Week 2 BM25 module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._BM25Index


_BM25Index = _load_bm25_index_class()

from week3_rag_adapter import Week3Chunk, chunk_policy_documents


SECTION_AWARE_CHUNKS = chunk_policy_documents(ROOT, "section_aware")
CHUNKS_BY_ID = {chunk.chunk_id: chunk for chunk in SECTION_AWARE_CHUNKS}
BM25_INDEX = _BM25Index(SECTION_AWARE_CHUNKS)
ELIGIBLE_POLICY_IDS = {chunk.policy_id for chunk in SECTION_AWARE_CHUNKS}


def _result(chunk: Week3Chunk, score: float) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "source_reference": chunk.metadata["source_reference"],
        "section_heading": chunk.section_heading,
        "jurisdiction": chunk.metadata["jurisdiction"],
        "currency": chunk.metadata["currency"],
        "policy_id": chunk.policy_id,
        "text": chunk.text,
        "score": score,
    }


def search_policy(query: str, policy_id: str, top_k: int = 5) -> list[dict]:
    """Search section-aware policy chunks for one eligible policy."""
    if policy_id not in ELIGIBLE_POLICY_IDS:
        raise ValueError(f"Unknown or excluded policy ID: {policy_id}")
    if not query.strip() or top_k <= 0:
        return []

    matches = BM25_INDEX.search(query, top_k, policy_id=policy_id)
    return [
        _result(CHUNKS_BY_ID[match.chunk_id], match.score)
        for match in matches
        if match.policy_id == policy_id
    ]


__all__ = ["search_policy"]

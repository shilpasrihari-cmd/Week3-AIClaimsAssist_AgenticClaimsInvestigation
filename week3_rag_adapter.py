"""Convert the approved Week 3 policy documents into RAG chunks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Week2_AIClaimsAssist_RAG.ingestion.chunker import (
    fixed_size_chunks,
    section_aware_chunks,
)
from Week2_AIClaimsAssist_RAG.ingestion.document_loader import DocumentExtraction

from policy_loader import PolicyDocument, load_policy_documents


@dataclass(frozen=True)
class Week3Chunk:
    """A Week 2-compatible chunk with the Week 3 policy metadata contract."""

    text: str
    policy_id: str
    document_id: str
    source_filename: str
    document_type: str
    section_heading: str
    chunk_id: str
    chunking_strategy: str
    metadata: dict[str, str]


def _as_extraction(document: PolicyDocument) -> DocumentExtraction:
    return DocumentExtraction(
        source_filename=Path(document.source_reference).name,
        document_id=document.doc_id,
        file_type=document.file_format.upper(),
        extracted_text=document.extracted_text,
        extracted_character_count=len(document.extracted_text),
        extraction_succeeded=document.extraction_succeeded,
    )


def _adapt_chunk(document: PolicyDocument, chunk, strategy: str) -> Week3Chunk:
    source_filename = Path(document.source_reference).name
    metadata = {
        "policy_id": document.policy_id,
        "document_id": document.doc_id,
        "jurisdiction": document.jurisdiction,
        "currency": document.currency,
        "insurance_type": document.insurance_type,
        "insurance_market": document.insurance_market,
        "source_reference": document.source_reference,
        "source_filename": source_filename,
        "document_type": document.doc_type,
        "section_heading": chunk.section_heading,
        "chunking_strategy": strategy,
    }
    return Week3Chunk(
        text=chunk.text,
        policy_id=document.policy_id,
        document_id=document.doc_id,
        source_filename=source_filename,
        document_type=document.doc_type,
        section_heading=chunk.section_heading,
        chunk_id=chunk.chunk_id,
        chunking_strategy=strategy,
        metadata=metadata,
    )


def chunk_policy_documents(
    workspace_root: str | Path,
    strategy: str,
) -> list[Week3Chunk]:
    """Load the manifest allow-list and chunk its approved documents only."""
    if strategy not in {"fixed_size", "section_aware"}:
        raise ValueError("strategy must be 'fixed_size' or 'section_aware'")

    documents = load_policy_documents(workspace_root)
    chunks: list[Week3Chunk] = []
    for document in documents:
        extraction = _as_extraction(document)
        base_chunks = (
            fixed_size_chunks(extraction)
            if strategy == "fixed_size"
            else section_aware_chunks(extraction)
        )
        chunks.extend(_adapt_chunk(document, chunk, strategy) for chunk in base_chunks)
    return chunks


__all__ = ["Week3Chunk", "chunk_policy_documents"]

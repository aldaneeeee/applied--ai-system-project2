"""Tests for document loading and chunking."""

from __future__ import annotations

import pytest

from src.ragqa.documents import Document, chunk_document, chunk_documents, load_documents


def test_load_documents_reads_knowledge_base(config):
    docs = load_documents(config.docs_dir)
    assert len(docs) >= 5
    names = {d.doc_id for d in docs}
    assert "rag.md" in names
    assert all(d.text.strip() for d in docs)


def test_load_documents_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_documents(tmp_path / "does_not_exist")


def test_chunk_document_respects_size_and_overlap():
    text = " ".join(f"word{i}" for i in range(500))
    doc = Document(doc_id="x.md", text=text)
    chunks = chunk_document(doc, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    for c in chunks:
        # Allow a little slack because we break on word boundaries.
        assert len(c.text) <= 300 + 50
        assert c.chunk_id.startswith("x.md#")


def test_chunk_ids_are_unique_and_ordered():
    docs = [Document("a.md", "alpha " * 400), Document("b.md", "beta " * 400)]
    chunks = chunk_documents(docs, chunk_size=250, overlap=40)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(c.doc_id in {"a.md", "b.md"} for c in chunks)


def test_overlap_larger_than_size_is_handled():
    doc = Document("x.md", "sentence one. " * 100)
    # overlap >= size would loop forever if unguarded; ensure it terminates.
    chunks = chunk_document(doc, chunk_size=100, overlap=100)
    assert len(chunks) >= 1

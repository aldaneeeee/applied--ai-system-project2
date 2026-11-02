"""Tests for the TF-IDF retriever."""

from __future__ import annotations

import pytest

from src.ragqa.retriever import TfidfRetriever


def test_build_and_retrieve_ranks_relevant_chunk_first(sample_chunks):
    r = TfidfRetriever().build(sample_chunks)
    results = r.retrieve(["What does TF-IDF stand for?"], top_k=2)
    assert results
    assert results[0].chunk_id == "a.md#0"
    assert results[0].score > 0


def test_retrieve_respects_top_k(sample_chunks):
    r = TfidfRetriever().build(sample_chunks)
    assert len(r.retrieve(["vectors"], top_k=1)) == 1
    assert len(r.retrieve(["vectors"], top_k=3)) == 3


def test_empty_queries_return_nothing(sample_chunks):
    r = TfidfRetriever().build(sample_chunks)
    assert r.retrieve([], top_k=3) == []
    assert r.retrieve(["   "], top_k=3) == []


def test_build_requires_chunks():
    with pytest.raises(ValueError):
        TfidfRetriever().build([])


def test_save_and_load_roundtrip(sample_chunks, tmp_path):
    TfidfRetriever().build(sample_chunks).save(tmp_path)
    loaded = TfidfRetriever.load(tmp_path)
    assert loaded.num_chunks == len(sample_chunks)
    results = loaded.retrieve(["cosine similarity angle"], top_k=1)
    assert results[0].chunk_id == "a.md#1"


def test_load_missing_index_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        TfidfRetriever.load(tmp_path / "nope")

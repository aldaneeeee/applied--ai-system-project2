"""Tests for the deterministic offline backend."""

from __future__ import annotations

from src.ragqa.documents import Chunk
from src.ragqa.llm import REFUSAL, OfflineBackend, content_words


def _contexts():
    return [
        Chunk("a.md#0", "a.md", "Cosine similarity measures the angle between two vectors."),
        Chunk("a.md#1", "a.md", "TF-IDF stands for Term Frequency Inverse Document Frequency."),
    ]


def test_plan_queries_includes_question_and_keywords():
    plan = OfflineBackend().plan_queries("What is cosine similarity?")
    assert "What is cosine similarity?" in plan.queries
    assert len(plan.queries) >= 1


def test_synthesize_answer_extracts_and_cites():
    res = OfflineBackend().synthesize_answer("What is cosine similarity?", _contexts())
    assert res.answer != REFUSAL
    assert "cosine" in res.answer.lower()
    assert res.citations  # cited at least one context
    assert all(1 <= c <= len(_contexts()) for c in res.citations)


def test_synthesize_answer_refuses_without_context():
    res = OfflineBackend().synthesize_answer("anything", [])
    assert res.answer == REFUSAL
    assert res.citations == []


def test_verify_flags_ungrounded_answer():
    verdict = OfflineBackend().verify_answer(
        "What is cosine similarity?",
        "The moon is made of cheese and orbits Jupiter every fortnight.",
        _contexts(),
    )
    assert verdict.grounded is False
    assert verdict.unsupported_claims


def test_verify_passes_grounded_answer():
    grounded_answer = "Cosine similarity measures the angle between two vectors."
    verdict = OfflineBackend().verify_answer("cosine?", grounded_answer, _contexts())
    assert verdict.grounded is True


def test_verify_treats_refusal_as_grounded():
    verdict = OfflineBackend().verify_answer("q", REFUSAL, _contexts())
    assert verdict.grounded is True


def test_content_words_drops_stopwords():
    assert "the" not in content_words("the cosine of the angle")
    assert "cosine" in content_words("the cosine of the angle")

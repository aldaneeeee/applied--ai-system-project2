"""End-to-end tests for the agentic RAG pipeline (offline backend)."""

from __future__ import annotations


def test_answerable_question_is_grounded_and_cited(pipeline):
    result = pipeline.answer("What does TF-IDF stand for?")
    assert not result.abstained
    assert result.grounded
    assert result.citations
    assert "vector_search.md" in result.cited_sources()
    assert "frequency" in result.answer.lower()


def test_out_of_scope_question_abstains(pipeline):
    result = pipeline.answer("Who won the 2022 FIFA World Cup?")
    assert result.abstained
    assert result.citations == []


def test_empty_input_is_rejected(pipeline):
    result = pipeline.answer("   ")
    assert result.abstained
    assert "question" in result.answer.lower()


def test_too_long_input_is_rejected(pipeline):
    result = pipeline.answer("a " * 2000)
    assert result.abstained
    assert "too long" in result.answer.lower()


def test_trace_records_all_stages(pipeline):
    result = pipeline.answer("What is cosine similarity?")
    steps = [step["step"] for step in result.trace]
    assert "plan" in steps
    assert "retrieve" in steps
    assert "answer" in steps
    assert "verify" in steps


def test_result_reports_backend(pipeline):
    result = pipeline.answer("What is a system prompt?")
    assert result.backend == "offline"

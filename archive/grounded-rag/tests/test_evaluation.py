"""Tests for the evaluation harness."""

from __future__ import annotations

from src.ragqa.evaluation import _keyword_recall, load_eval_items, run_evaluation


def test_load_eval_items(config):
    items = load_eval_items(config.eval_file)
    assert len(items) >= 10
    assert any(i.should_answer for i in items)
    assert any(not i.should_answer for i in items)


def test_keyword_recall_phrase_matching():
    assert _keyword_recall("term frequency and document counts", ["term frequency"]) == 1.0
    assert _keyword_recall("nothing relevant here", ["term frequency"]) == 0.0
    assert _keyword_recall("anything", []) == 1.0


def test_run_evaluation_reports_metrics(config, pipeline):
    report = run_evaluation(config, pipeline=pipeline)
    m = report.metrics
    assert m["total"] >= 10
    # The system must answer answerable questions and refuse the rest.
    assert m["abstention_accuracy"] == 1.0
    # Answered questions should be verified as grounded.
    assert m["groundedness_rate"] == 1.0
    # Retrieval should surface at least one expected source on average.
    assert m["retrieval_hit_rate"] >= 0.8
    for key in ("keyword_recall", "answerable_answered", "retrieval_checked"):
        assert key in m

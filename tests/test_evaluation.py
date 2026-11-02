"""The evaluation harness itself is tested, so a regression in the AI DJ fails CI."""

from src.evaluate import load_cases, run_evaluation
from src.llm import OfflineBackend


def test_eval_set_is_well_formed():
    cases = load_cases()
    assert len(cases) >= 20
    assert len({c["id"] for c in cases}) == len(cases)
    assert {"ok", "out_of_scope", "rejected"} <= {c["expect_status"] for c in cases}


def test_core_eval_cases_all_pass_offline():
    _, rows, _ = run_evaluation(backend=OfflineBackend())
    core_failures = [r["id"] for r in rows if r["split"] == "core" and not r["passed"]]
    assert core_failures == []


def test_offline_never_answers_off_topic_requests():
    _, rows, _ = run_evaluation(backend=OfflineBackend())
    for r in rows:
        if r["id"].startswith("off-topic"):
            assert r["status"] == "out_of_scope"

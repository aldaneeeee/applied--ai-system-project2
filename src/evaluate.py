"""
Reliability evaluation for the AI DJ.

Runs every request in data/eval/dj_eval.jsonl through the full AI DJ workflow
and checks the result against what a person expected:

  status accuracy      - answered / refused-as-off-topic / rejected correctly
  genre accuracy       - interpreted genre matches the expected genre
  mood accuracy        - interpreted mood matches the expected mood
  energy in range      - interpreted energy falls inside the expected range
  top-3 hit rate       - an expected song appears in the top 3 recommendations
  explanation checked  - the AI explanation passed the self-check on its own
                         (no fallback to the rule-based reasons was needed)

Usage:
  python -m src.evaluate                    # uses DJ_BACKEND (default auto)
  python -m src.evaluate --backend offline
Cases are split into "core" (expected behavior, must pass) and "challenge"
(harder phrasings written after the offline rules, kept as an honest measure of
weaknesses). A JSON report is also written to logs/eval_report.json.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_dj import AIDJ  # noqa: E402
from src.llm import get_backend  # noqa: E402
from src.logging_setup import configure_logging  # noqa: E402
from src.recommender import load_songs  # noqa: E402

EVAL_FILE = PROJECT_ROOT / "data" / "eval" / "dj_eval.jsonl"
REPORT_FILE = PROJECT_ROOT / "logs" / "eval_report.json"


def load_cases(path: Path = EVAL_FILE):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _as_list(value):
    """Expected values may be one string or a list of acceptable strings."""
    return value if isinstance(value, list) else [value]


def evaluate_case(dj: AIDJ, case: dict) -> dict:
    """Run one case and return which checks passed (None = not applicable)."""
    result = dj.run(case["request"], k=5)
    profile = result.profile or {}
    top3 = [s["title"] for s, _, _ in result.recommendations[:3]]
    checks = {"status": result.status == case["expect_status"]}
    if result.status == "ok" and case["expect_status"] == "ok":
        if "expect_genre" in case:
            checks["genre"] = profile.get("genre") in _as_list(case["expect_genre"])
        if "expect_mood" in case:
            checks["mood"] = profile.get("mood") in _as_list(case["expect_mood"])
        if "energy_range" in case:
            lo, hi = case["energy_range"]
            checks["energy"] = lo <= profile.get("energy", -1) <= hi
        if "expect_in_top3" in case:
            checks["top3"] = any(t in top3 for t in case["expect_in_top3"])
        checks["explanation"] = result.explanation_source != "template-fallback"
    return {
        "id": case["id"],
        "split": case.get("split", "core"),
        "request": case["request"],
        "status": result.status,
        "profile": result.profile,
        "top3": top3,
        "explanation_source": result.explanation_source,
        "warnings": result.warnings,
        "checks": checks,
        "passed": all(checks.values()),
    }


def summarize(rows) -> dict:
    metrics = {}
    for name in ["status", "genre", "mood", "energy", "top3", "explanation"]:
        values = [r["checks"][name] for r in rows if name in r["checks"]]
        if values:
            metrics[name] = {"passed": sum(values), "total": len(values),
                             "rate": round(sum(values) / len(values), 3)}
    metrics["cases_fully_passed"] = {"passed": sum(r["passed"] for r in rows), "total": len(rows)}
    return metrics


def run_evaluation(backend=None, cases=None):
    songs = load_songs(str(PROJECT_ROOT / "data" / "songs.csv"))
    dj = AIDJ(songs, backend=backend if backend is not None else get_backend())
    rows = [evaluate_case(dj, c) for c in (cases if cases is not None else load_cases())]
    return dj.backend.name, rows, summarize(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the AI DJ on the gold request set")
    parser.add_argument("--backend", choices=["auto", "claude", "offline"])
    args = parser.parse_args(argv)
    configure_logging()

    backend_name, rows, metrics = run_evaluation(get_backend(args.backend))
    by_split = {split: summarize([r for r in rows if r["split"] == split])
                for split in ("core", "challenge") if any(r["split"] == split for r in rows)}

    labels = {"status": "Status accuracy", "genre": "Genre accuracy", "mood": "Mood accuracy",
              "energy": "Energy in range", "top3": "Top-3 hit rate",
              "explanation": "Explanation self-check"}
    print(f"\nAI DJ evaluation  (backend={backend_name}, {len(rows)} cases)")
    for split, split_metrics in by_split.items():
        full = split_metrics["cases_fully_passed"]
        print(f"\n  [{split}]  {full['passed']}/{full['total']} cases fully passed")
        for key, label in labels.items():
            if key in split_metrics:
                m = split_metrics[key]
                print(f"    {label:<24} {m['passed']:>2}/{m['total']:<2}  {m['rate']:.0%}")

    failures = [r for r in rows if not r["passed"]]
    if failures:
        print("\nFailed cases:")
        for r in failures:
            failed = [k for k, v in r["checks"].items() if not v]
            print(f"  - {r['id']}: failed {failed}; got status={r['status']}, "
                  f"profile={r['profile']}, top3={r['top3']}")

    try:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(json.dumps(
            {"backend": backend_name, "metrics": metrics, "metrics_by_split": by_split,
             "cases": rows}, indent=2))
        print(f"\nFull report: {REPORT_FILE.relative_to(PROJECT_ROOT)}")
    except OSError as exc:
        print(f"\n(Could not write report: {exc})")
    # Challenge cases are deliberately hard and documented as known weaknesses,
    # so only a failure in the core set counts as a regression.
    return 0 if not any(r["split"] == "core" for r in failures) else 1


if __name__ == "__main__":
    sys.exit(main())

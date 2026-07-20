"""Reliability / evaluation harness.

Runs the pipeline over a gold set of question/answer expectations and measures
how well it behaves. This is what makes the system's quality *measurable* rather
than anecdotal. Metrics reported:

* abstention accuracy - does it answer answerable questions and refuse
  unanswerable ones? (the core safety behaviour)
* keyword recall      - do answers contain the expected key facts?
* groundedness rate   - are answered questions verified as grounded?
* retrieval hit rate   - did retrieval surface at least one expected source?

The gold set lives in ``data/eval/qa_eval.jsonl`` (one JSON object per line).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .llm import content_words
from .logging_setup import get_logger
from .pipeline import RagPipeline, RagResult

logger = get_logger()


@dataclass
class EvalItem:
    id: str
    question: str
    should_answer: bool = True
    expected_keywords: list[str] = field(default_factory=list)
    expected_sources: list[str] = field(default_factory=list)


@dataclass
class CaseResult:
    item: EvalItem
    result: RagResult
    abstention_correct: bool
    keyword_recall: float | None  # None when not applicable
    grounded_ok: bool | None
    retrieval_hit: bool | None


@dataclass
class EvalReport:
    cases: list[CaseResult]
    metrics: dict

    def summary_lines(self) -> list[str]:
        m = self.metrics
        return [
            f"Cases evaluated      : {m['total']}",
            f"Abstention accuracy  : {m['abstention_accuracy']:.0%} "
            f"({m['abstention_correct']}/{m['total']})",
            f"Keyword recall (avg) : {m['keyword_recall']:.0%} "
            f"(over {m['answerable_answered']} answered)",
            f"Groundedness rate    : {m['groundedness_rate']:.0%} "
            f"(over {m['answerable_answered']} answered)",
            f"Retrieval hit rate   : {m['retrieval_hit_rate']:.0%} "
            f"(over {m['retrieval_checked']} checked)",
        ]


def load_eval_items(path: Path) -> list[EvalItem]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation set not found: {path}")

    items: list[EvalItem] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
        items.append(
            EvalItem(
                id=str(data.get("id", f"item-{line_no}")),
                question=data["question"],
                should_answer=bool(data.get("should_answer", True)),
                expected_keywords=list(data.get("expected_keywords", [])),
                expected_sources=list(data.get("expected_sources", [])),
            )
        )
    if not items:
        raise ValueError(f"No evaluation items found in {path}")
    return items


def _keyword_recall(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    ans_words = content_words(answer)
    hits = 0
    for kw in keywords:
        kw_words = content_words(kw)
        # A keyword phrase counts as present if all its content words appear.
        if kw_words and kw_words <= ans_words:
            hits += 1
    return hits / len(keywords)


def evaluate_case(item: EvalItem, result: RagResult) -> CaseResult:
    answered = not result.abstained
    abstention_correct = answered == item.should_answer

    keyword_recall = None
    grounded_ok = None
    retrieval_hit = None

    if item.should_answer and answered:
        keyword_recall = _keyword_recall(result.answer, item.expected_keywords)
        grounded_ok = result.grounded
        if item.expected_sources:
            cited = set(result.cited_sources())
            # Also consider any retrieved source in the trace for a hit.
            retrieved = {
                c.split("#")[0]
                for step in result.trace
                if step.get("step") == "retrieve"
                for c in step.get("chunks", [])
            }
            hit_pool = cited | retrieved
            retrieval_hit = any(src in hit_pool for src in item.expected_sources)

    return CaseResult(
        item=item,
        result=result,
        abstention_correct=abstention_correct,
        keyword_recall=keyword_recall,
        grounded_ok=grounded_ok,
        retrieval_hit=retrieval_hit,
    )


def run_evaluation(config: Config, pipeline: RagPipeline | None = None) -> EvalReport:
    items = load_eval_items(config.eval_file)
    pipeline = pipeline or RagPipeline.from_config(config)

    cases: list[CaseResult] = []
    for item in items:
        logger.info("Evaluating %s: %s", item.id, item.question)
        result = pipeline.answer(item.question)
        cases.append(evaluate_case(item, result))

    total = len(cases)
    abstention_correct = sum(1 for c in cases if c.abstention_correct)

    recalls = [c.keyword_recall for c in cases if c.keyword_recall is not None]
    grounded = [c.grounded_ok for c in cases if c.grounded_ok is not None]
    retrieval_checks = [c.retrieval_hit for c in cases if c.retrieval_hit is not None]

    metrics = {
        "total": total,
        "abstention_correct": abstention_correct,
        "abstention_accuracy": abstention_correct / total if total else 0.0,
        "answerable_answered": len(recalls),
        "keyword_recall": sum(recalls) / len(recalls) if recalls else 0.0,
        "groundedness_rate": (sum(1 for g in grounded if g) / len(grounded)) if grounded else 0.0,
        "retrieval_checked": len(retrieval_checks),
        "retrieval_hit_rate": (
            sum(1 for h in retrieval_checks if h) / len(retrieval_checks)
            if retrieval_checks else 0.0
        ),
    }
    return EvalReport(cases=cases, metrics=metrics)

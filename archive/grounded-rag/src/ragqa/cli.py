"""Command-line interface for GroundedRAG.

Usage:
    python -m src.ragqa.cli ingest              # build/refresh the index
    python -m src.ragqa.cli ask "your question" # ask a single question
    python -m src.ragqa.cli eval                # run the evaluation harness
    python -m src.ragqa.cli demo                # canned end-to-end demo
"""

from __future__ import annotations

import argparse
import sys

from .config import load_config
from .logging_setup import configure_logging
from .pipeline import RagPipeline, RagResult, build_index

DIVIDER = "=" * 68


def _format_result(result: RagResult) -> str:
    lines = [DIVIDER, f"Q: {result.question}", "", result.answer, ""]

    if result.citations:
        lines.append("Sources:")
        for i, chunk in enumerate(result.citations, start=1):
            snippet = " ".join(chunk.text.split())[:140]
            lines.append(f"  [{i}] {chunk.doc_id} (score {chunk.score:.3f})")
            lines.append(f"      {snippet}...")

    status = []
    status.append(f"backend={result.backend}")
    status.append(f"grounded={result.grounded}")
    status.append(f"abstained={result.abstained}")
    status.append(f"attempts={result.attempts}")
    status.append(f"top_retrieval_score={result.retrieval_score:.3f}")
    lines.append("")
    lines.append("  ·  ".join(status))
    lines.append(DIVIDER)
    return "\n".join(lines)


def cmd_ingest(config) -> int:
    retriever = build_index(config)
    print(f"Ingested and indexed {retriever.num_chunks} chunks into {config.index_dir}")
    return 0


def cmd_ask(config, question: str) -> int:
    if not question or not question.strip():
        print("Please provide a question, e.g.  ask \"What is RAG?\"", file=sys.stderr)
        return 2
    pipeline = RagPipeline.from_config(config)
    result = pipeline.answer(question)
    print(_format_result(result))
    return 0


def cmd_eval(config) -> int:
    from .evaluation import run_evaluation

    report = run_evaluation(config)
    print(DIVIDER)
    print("EVALUATION REPORT")
    print(DIVIDER)
    for case in report.cases:
        verdict = "OK " if case.abstention_correct else "XX "
        answered = "answered" if not case.result.abstained else "abstained"
        extra = ""
        if case.keyword_recall is not None:
            extra = f" recall={case.keyword_recall:.0%} grounded={case.result.grounded}"
        print(f"  {verdict}{case.item.id:<4} [{answered}]{extra}  {case.item.question}")
    print(DIVIDER)
    for line in report.summary_lines():
        print("  " + line)
    print(DIVIDER)
    # Non-zero exit if abstention behaviour is wrong on any case (useful in CI).
    return 0 if report.metrics["abstention_correct"] == report.metrics["total"] else 1


def cmd_demo(config) -> int:
    print(f"Backend in use: {config.resolved_backend()} (model={config.model})\n")
    pipeline = RagPipeline.from_config(config)
    questions = [
        "What does TF-IDF stand for?",
        "How does RAG help reduce hallucination?",
        "What is a retrieval threshold?",
        "Who won the 2022 FIFA World Cup?",  # out of scope -> should abstain
    ]
    for q in questions:
        print(_format_result(pipeline.answer(q)))
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ragqa", description="GroundedRAG - retrieval-augmented, self-checking Q&A."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Build/refresh the retrieval index from data/docs.")

    ask = sub.add_parser("ask", help="Ask a single question.")
    ask.add_argument("question", nargs="+", help="The question to ask.")

    sub.add_parser("eval", help="Run the evaluation harness on the gold Q&A set.")
    sub.add_parser("demo", help="Run a canned end-to-end demonstration.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    configure_logging(config.log_level, config.log_dir)

    try:
        if args.command == "ingest":
            return cmd_ingest(config)
        if args.command == "ask":
            return cmd_ask(config, " ".join(args.question))
        if args.command == "eval":
            return cmd_eval(config)
        if args.command == "demo":
            return cmd_demo(config)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

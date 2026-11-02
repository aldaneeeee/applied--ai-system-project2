"""The agentic Retrieval-Augmented Generation pipeline.

This is the advanced AI feature at the core of the application. A single call to
:meth:`RagPipeline.answer` runs a multi-step, self-checking workflow:

    1. Guardrail  - validate the user's input.
    2. Plan       - the model turns the question into focused search queries.
    3. Retrieve   - vector search returns the most relevant passages.
    4. Guardrail  - if nothing is relevant enough, abstain instead of guessing.
    5. Answer     - the model answers using ONLY the retrieved passages, with
                    citations.
    6. Verify     - a separate self-check step confirms every claim is grounded
                    in the cited passages.
    7. Retry      - if the answer is not grounded, re-plan/re-retrieve and try
                    again (up to a configurable limit); otherwise abstain.

Every step is logged and captured in a machine-readable trace for observability
and evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .documents import Chunk, chunk_documents, load_documents
from .llm import REFUSAL, AnswerResult, PlanResult, VerifyResult, get_backend
from .logging_setup import get_logger
from .retriever import TfidfRetriever

logger = get_logger()

MAX_QUESTION_CHARS = 2000
LOW_CONFIDENCE_NOTE = (
    "I could not fully verify an answer against the documents, so I'm not "
    "confident enough to answer. Try rephrasing, or add supporting documents."
)


@dataclass
class RagResult:
    """The full, inspectable result of one pipeline run."""

    question: str
    answer: str
    citations: list[Chunk] = field(default_factory=list)
    grounded: bool = False
    abstained: bool = False
    backend: str = "offline"
    retrieval_score: float = 0.0
    attempts: int = 0
    trace: list[dict] = field(default_factory=list)

    def cited_sources(self) -> list[str]:
        """Distinct source documents backing the answer, in citation order."""
        seen: list[str] = []
        for c in self.citations:
            if c.doc_id not in seen:
                seen.append(c.doc_id)
        return seen


def build_index(config: Config) -> TfidfRetriever:
    """Load documents, chunk them, build the retriever, and persist it."""
    docs = load_documents(config.docs_dir)
    if not docs:
        raise ValueError(
            f"No usable documents found in {config.docs_dir}. Add .md/.txt/.pdf files."
        )
    chunks = chunk_documents(docs, config.chunk_size, config.chunk_overlap)
    retriever = TfidfRetriever().build(chunks)
    retriever.save(config.index_dir)
    return retriever


def _load_or_build_retriever(config: Config) -> TfidfRetriever:
    try:
        return TfidfRetriever.load(config.index_dir)
    except FileNotFoundError:
        logger.info("No prebuilt index found; building one now.")
        return build_index(config)


class RagPipeline:
    """Orchestrates the agentic RAG workflow."""

    def __init__(self, config: Config, retriever: TfidfRetriever, backend=None) -> None:
        self.config = config
        self.retriever = retriever
        self.backend = backend if backend is not None else get_backend(config)

    @classmethod
    def from_config(cls, config: Config) -> "RagPipeline":
        retriever = _load_or_build_retriever(config)
        return cls(config, retriever)

    # -- main entry point --------------------------------------------------
    def answer(self, question: str) -> RagResult:
        result = RagResult(question=question, backend=self.backend.name, answer="")

        # (1) Input guardrail --------------------------------------------
        cleaned = (question or "").strip()
        if not cleaned:
            result.answer = "Please enter a question."
            result.abstained = True
            result.trace.append({"step": "guardrail", "detail": "empty question"})
            return result
        if len(cleaned) > MAX_QUESTION_CHARS:
            result.answer = (
                f"That question is too long (limit {MAX_QUESTION_CHARS} characters). "
                "Please shorten it."
            )
            result.abstained = True
            result.trace.append({"step": "guardrail", "detail": "question too long"})
            return result

        best_answer: AnswerResult | None = None
        best_contexts: list[Chunk] = []

        # Agentic loop: attempt, self-check, and retry if ungrounded.
        for attempt in range(self.config.max_retries + 1):
            result.attempts = attempt + 1

            # (2) Plan ---------------------------------------------------
            plan: PlanResult = self.backend.plan_queries(cleaned)
            if attempt > 0:
                # Broaden retrieval on a retry by adding the raw question and
                # first-attempt context sources as extra query signal.
                plan.queries = list(dict.fromkeys(plan.queries + [cleaned]))
            result.trace.append(
                {"step": "plan", "attempt": result.attempts, "queries": plan.queries,
                 "rationale": plan.rationale}
            )
            logger.info("[attempt %d] plan queries: %s", result.attempts, plan.queries)

            # (3) Retrieve ----------------------------------------------
            contexts = self.retriever.retrieve(plan.queries, top_k=self.config.top_k)
            top_score = contexts[0].score if contexts else 0.0
            result.retrieval_score = max(result.retrieval_score, top_score)
            result.trace.append(
                {"step": "retrieve", "attempt": result.attempts, "top_score": top_score,
                 "chunks": [c.chunk_id for c in contexts]}
            )
            logger.info("[attempt %d] retrieved %d chunks (top score %.3f)",
                        result.attempts, len(contexts), top_score)

            # (4) Retrieval guardrail -----------------------------------
            if not contexts or top_score < self.config.min_score:
                result.trace.append(
                    {"step": "guardrail", "detail": "retrieval below threshold",
                     "top_score": top_score, "threshold": self.config.min_score}
                )
                logger.info("Retrieval below threshold; abstaining.")
                result.answer = REFUSAL
                result.abstained = True
                result.citations = []
                return result

            # (5) Answer -------------------------------------------------
            answer_res = self.backend.synthesize_answer(cleaned, contexts)
            result.trace.append(
                {"step": "answer", "attempt": result.attempts,
                 "citations": answer_res.citations,
                 "is_refusal": answer_res.answer.strip() == REFUSAL}
            )

            # Model chose to refuse despite having context.
            if answer_res.answer.strip() == REFUSAL:
                result.answer = REFUSAL
                result.abstained = True
                result.citations = []
                return result

            # (6) Verify -------------------------------------------------
            verdict: VerifyResult = self.backend.verify_answer(
                cleaned, answer_res.answer, contexts
            )
            result.trace.append(
                {"step": "verify", "attempt": result.attempts, "grounded": verdict.grounded,
                 "reason": verdict.reason, "unsupported": verdict.unsupported_claims}
            )
            logger.info("[attempt %d] grounded=%s (%s)",
                        result.attempts, verdict.grounded, verdict.reason)

            best_answer, best_contexts = answer_res, contexts

            if verdict.grounded:
                result.answer = answer_res.answer
                result.grounded = True
                result.citations = self._citations_for(answer_res, contexts)
                return result

            # (7) Not grounded -> loop and retry if attempts remain.
            logger.info("Answer not grounded; %s",
                        "retrying" if attempt < self.config.max_retries else "abstaining")

        # Exhausted retries without a grounded answer -> abstain safely.
        result.answer = LOW_CONFIDENCE_NOTE
        result.abstained = True
        result.grounded = False
        result.citations = []
        if best_answer is not None:
            result.trace.append(
                {"step": "final", "detail": "ungrounded after retries",
                 "discarded_answer": best_answer.answer}
            )
        return result

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _citations_for(answer_res: AnswerResult, contexts: list[Chunk]) -> list[Chunk]:
        """Map the answer's 1-based citation indices back to Chunk objects.

        Falls back to all retrieved contexts if the model gave no citations but
        produced a real answer (so the user can still see the supporting text).
        """
        if answer_res.citations:
            picked = []
            for i in answer_res.citations:
                if 1 <= i <= len(contexts):
                    picked.append(contexts[i - 1])
            if picked:
                return picked
        return contexts

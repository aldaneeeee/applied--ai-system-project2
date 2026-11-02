"""LLM backends for the pipeline stages.

Two interchangeable backends implement the same interface:

* :class:`AnthropicBackend` - uses Claude for planning, answering and
  verification via the Messages API with structured (JSON-schema) outputs.
* :class:`OfflineBackend` - a fully deterministic, dependency-free fallback
  that performs extractive answering and lexical grounding checks. It requires
  no API key and no network, which keeps the whole system reproducible and lets
  the test-suite and a demo run anywhere.

The active backend is chosen by :func:`get_backend` based on configuration.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .config import Config
from .documents import Chunk
from .logging_setup import get_logger
from . import prompts

logger = get_logger()

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "been", "being", "with", "as", "by", "that", "this",
    "it", "its", "at", "from", "into", "how", "what", "why", "when", "which",
    "who", "does", "do", "can", "will", "would", "should", "about", "these",
    "those", "than", "then", "there", "their", "they", "you", "your", "we",
}


class LLMError(RuntimeError):
    """Raised when an LLM backend cannot produce a result."""


# --- Result types shared by both backends ---------------------------------
@dataclass
class PlanResult:
    queries: list[str]
    rationale: str = ""


@dataclass
class AnswerResult:
    answer: str
    citations: list[int] = field(default_factory=list)  # 1-based indices into contexts


@dataclass
class VerifyResult:
    grounded: bool
    unsupported_claims: list[str] = field(default_factory=list)
    reason: str = ""


# --- Text helpers ----------------------------------------------------------
def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def content_words(text: str) -> set[str]:
    return {t for t in tokenize(text) if t not in _STOPWORDS and len(t) > 2}


REFUSAL = "I don't have enough information in the provided documents to answer that."


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


# ===========================================================================
# Offline (deterministic) backend
# ===========================================================================
class OfflineBackend:
    """Deterministic backend: extractive answers + lexical grounding checks."""

    name = "offline"

    def plan_queries(self, question: str) -> PlanResult:
        queries = [question.strip()]
        # A keyword-only variant helps TF-IDF focus on content words.
        keywords = " ".join(sorted(content_words(question)))
        if keywords and keywords != question.strip().lower():
            queries.append(keywords)
        return PlanResult(queries=queries, rationale="keyword-expansion (offline)")

    def synthesize_answer(self, question: str, contexts: list[Chunk]) -> AnswerResult:
        if not contexts:
            return AnswerResult(answer=REFUSAL, citations=[])

        q_words = content_words(question)
        scored: list[tuple[float, int, str]] = []
        for idx, chunk in enumerate(contexts, start=1):
            for sentence in _split_sentences(chunk.text):
                overlap = len(q_words & content_words(sentence))
                if overlap:
                    scored.append((overlap, idx, sentence))

        if not scored:
            return AnswerResult(answer=REFUSAL, citations=[])

        # Take the best few sentences, keep original context order for readability.
        scored.sort(key=lambda s: s[0], reverse=True)
        top = scored[:3]
        top.sort(key=lambda s: s[1])

        cited: list[int] = []
        pieces: list[str] = []
        for _, idx, sentence in top:
            if idx not in cited:
                cited.append(idx)
            pieces.append(f"{sentence} [{idx}]")

        return AnswerResult(answer=" ".join(pieces), citations=cited)

    def verify_answer(self, question: str, answer: str, contexts: list[Chunk]) -> VerifyResult:
        if answer.strip() == REFUSAL:
            return VerifyResult(grounded=True, reason="refusal is grounded by definition")

        support = set()
        for chunk in contexts:
            support |= content_words(chunk.text)

        ans_words = content_words(answer)
        if not ans_words:
            return VerifyResult(grounded=False, reason="empty answer")

        covered = ans_words & support
        coverage = len(covered) / len(ans_words)
        unsupported = sorted(ans_words - support)[:10]
        grounded = coverage >= 0.6
        return VerifyResult(
            grounded=grounded,
            unsupported_claims=[] if grounded else unsupported,
            reason=f"lexical grounding coverage={coverage:.2f}",
        )


# ===========================================================================
# Anthropic (Claude) backend
# ===========================================================================
class AnthropicBackend:
    """Backend that uses Claude for each pipeline stage."""

    name = "anthropic"

    def __init__(self, config: Config) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - guarded by config
            raise LLMError(
                "The `anthropic` package is required for the anthropic backend. "
                "Install it with `pip install anthropic`, or set RAGQA_BACKEND=offline."
            ) from exc

        if not config.api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY is not set. Set it in your environment/.env, "
                "or set RAGQA_BACKEND=offline to run without a key."
            )

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=config.api_key)
        self._model = config.model
        self._offline = OfflineBackend()  # used as a safety net on hard failures

    # -- low-level structured call ----------------------------------------
    def _json_call(self, system: str, user: str, schema: dict, max_tokens: int = 1024) -> dict:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except self._anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API error ({exc.status_code}): {exc.message}") from exc
        except self._anthropic.APIConnectionError as exc:
            raise LLMError(f"Could not reach the Claude API: {exc}") from exc

        if response.stop_reason == "refusal":
            raise LLMError("The model declined to respond to this request.")

        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model did not return valid JSON: {text[:200]}") from exc

    # -- pipeline stages ---------------------------------------------------
    def plan_queries(self, question: str) -> PlanResult:
        schema = {
            "type": "object",
            "properties": {
                "queries": {"type": "array", "items": {"type": "string"}},
                "rationale": {"type": "string"},
            },
            "required": ["queries", "rationale"],
            "additionalProperties": False,
        }
        try:
            data = self._json_call(prompts.PLAN_SYSTEM, f"Question: {question}", schema, 512)
            queries = [q for q in data.get("queries", []) if q.strip()][:3]
            if not queries:
                queries = [question]
            return PlanResult(queries=queries, rationale=data.get("rationale", ""))
        except LLMError as exc:
            logger.warning("Planning fell back to the raw question: %s", exc)
            return PlanResult(queries=[question], rationale="fallback: planning failed")

    def synthesize_answer(self, question: str, contexts: list[Chunk]) -> AnswerResult:
        if not contexts:
            return AnswerResult(answer=REFUSAL, citations=[])
        schema = {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "citations": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["answer", "citations"],
            "additionalProperties": False,
        }
        data = self._json_call(
            prompts.ANSWER_SYSTEM,
            prompts.answer_user_prompt(question, contexts),
            schema,
            1024,
        )
        citations = [c for c in data.get("citations", []) if 1 <= int(c) <= len(contexts)]
        return AnswerResult(answer=data.get("answer", "").strip(), citations=citations)

    def verify_answer(self, question: str, answer: str, contexts: list[Chunk]) -> VerifyResult:
        schema = {
            "type": "object",
            "properties": {
                "grounded": {"type": "boolean"},
                "unsupported_claims": {"type": "array", "items": {"type": "string"}},
                "reason": {"type": "string"},
            },
            "required": ["grounded", "unsupported_claims", "reason"],
            "additionalProperties": False,
        }
        try:
            data = self._json_call(
                prompts.VERIFY_SYSTEM,
                prompts.verify_user_prompt(question, answer, contexts),
                schema,
                768,
            )
            return VerifyResult(
                grounded=bool(data.get("grounded", False)),
                unsupported_claims=list(data.get("unsupported_claims", [])),
                reason=data.get("reason", ""),
            )
        except LLMError as exc:
            # If the verifier itself fails, fall back to the deterministic check
            # rather than silently trusting the answer.
            logger.warning("Verifier fell back to lexical grounding: %s", exc)
            return self._offline.verify_answer(question, answer, contexts)


def get_backend(config: Config):
    """Return the backend implied by the configuration."""
    resolved = config.resolved_backend()
    if resolved == "anthropic":
        logger.info("Using Anthropic backend (model=%s)", config.model)
        return AnthropicBackend(config)
    logger.info("Using offline deterministic backend")
    return OfflineBackend()

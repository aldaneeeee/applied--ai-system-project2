"""Prompt templates for the Claude-backed pipeline stages.

Keeping prompts in one module makes the model's instructions easy to review and
tune without touching pipeline logic.
"""

from __future__ import annotations

from .documents import Chunk

PLAN_SYSTEM = """You are the planning step of a retrieval-augmented QA system.
Given a user's question, produce 1-3 focused search queries that would retrieve
the passages needed to answer it. Expand abbreviations, split multi-part
questions, and include synonyms. Do not answer the question."""

ANSWER_SYSTEM = """You are a careful research assistant. Answer the user's
question USING ONLY the numbered context passages provided. Follow these rules:

1. Ground every statement in the passages. Do not use outside knowledge.
2. Cite the passages you used with bracketed numbers like [1] or [2], matching
   the numbers shown in the context.
3. If the passages do not contain enough information to answer, respond with
   exactly: "I don't have enough information in the provided documents to answer
   that." and set an empty citation list.
4. Be concise and lead with the direct answer."""

VERIFY_SYSTEM = """You are the verification step of a QA system. You are given a
question, a proposed answer, and the numbered context passages the answer was
supposed to be based on. Decide whether EVERY claim in the answer is directly
supported by the passages.

- If the answer is the explicit "not enough information" refusal, it is grounded.
- List any specific claims that are NOT supported by the passages.
- Be strict: an answer that adds facts beyond the passages is NOT grounded."""


def format_contexts(contexts: list[Chunk]) -> str:
    """Render retrieved chunks as a numbered context block for the model."""
    lines = []
    for i, chunk in enumerate(contexts, start=1):
        lines.append(f"[{i}] (source: {chunk.doc_id})\n{chunk.text}")
    return "\n\n".join(lines)


def answer_user_prompt(question: str, contexts: list[Chunk]) -> str:
    return (
        f"Question: {question}\n\n"
        f"Context passages:\n{format_contexts(contexts)}\n\n"
        "Answer the question using only these passages, with bracketed citations."
    )


def verify_user_prompt(question: str, answer: str, contexts: list[Chunk]) -> str:
    return (
        f"Question: {question}\n\n"
        f"Proposed answer:\n{answer}\n\n"
        f"Context passages:\n{format_contexts(contexts)}\n\n"
        "Is every claim in the answer supported by the passages?"
    )

"""Shared pytest fixtures.

The whole suite runs against the deterministic offline backend so it needs no
API key and no network, and produces identical results on any machine.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Force the reproducible offline backend before any ragqa module is imported.
os.environ["RAGQA_BACKEND"] = "offline"

# Make the `src` package importable when tests run from the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402

from src.ragqa.config import load_config  # noqa: E402
from src.ragqa.documents import Chunk, chunk_documents, load_documents  # noqa: E402
from src.ragqa.pipeline import RagPipeline  # noqa: E402
from src.ragqa.retriever import TfidfRetriever  # noqa: E402


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    return [
        Chunk("a.md#0", "a.md", "TF-IDF stands for Term Frequency Inverse Document Frequency."),
        Chunk("a.md#1", "a.md", "Cosine similarity measures the angle between two vectors."),
        Chunk("b.md#0", "b.md", "A system prompt sets the model's role and rules."),
    ]


@pytest.fixture
def retriever(config) -> TfidfRetriever:
    """A retriever built in memory from the real knowledge base (no disk writes)."""
    docs = load_documents(config.docs_dir)
    chunks = chunk_documents(docs, config.chunk_size, config.chunk_overlap)
    return TfidfRetriever().build(chunks)


@pytest.fixture
def pipeline(config, retriever) -> RagPipeline:
    return RagPipeline(config, retriever)

"""Central configuration.

All tunable behaviour lives here and is driven by environment variables (which
may be supplied via a `.env` file). Every setting has a safe default so the
application runs out of the box, even with no configuration at all.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # Loading .env is a convenience; the app still works without python-dotenv.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - optional dependency / malformed .env
    pass


# Project layout ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCS_DIR = PROJECT_ROOT / "data" / "docs"
DEFAULT_INDEX_DIR = PROJECT_ROOT / "index"
DEFAULT_EVAL_FILE = PROJECT_ROOT / "data" / "eval" / "qa_eval.jsonl"
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

VALID_BACKENDS = {"auto", "anthropic", "offline"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Config:
    """Resolved application configuration."""

    # Backend / model
    api_key: str | None = None
    model: str = "claude-opus-4-8"
    backend: str = "auto"  # auto | anthropic | offline

    # Retrieval / pipeline
    top_k: int = 4
    min_score: float = 0.12
    max_retries: int = 1
    chunk_size: int = 900
    chunk_overlap: int = 150

    # Paths
    docs_dir: Path = field(default_factory=lambda: DEFAULT_DOCS_DIR)
    index_dir: Path = field(default_factory=lambda: DEFAULT_INDEX_DIR)
    eval_file: Path = field(default_factory=lambda: DEFAULT_EVAL_FILE)
    log_dir: Path = field(default_factory=lambda: DEFAULT_LOG_DIR)

    # Logging
    log_level: str = "INFO"

    def resolved_backend(self) -> str:
        """Decide which backend will actually be used.

        `auto` resolves to `anthropic` only when a key is present AND the
        anthropic SDK is importable; otherwise it degrades to `offline`.
        """
        if self.backend == "offline":
            return "offline"
        if self.backend == "anthropic":
            return "anthropic"
        # auto
        if self.api_key:
            try:
                import anthropic  # noqa: F401

                return "anthropic"
            except Exception:
                return "offline"
        return "offline"


def load_config() -> Config:
    """Build a :class:`Config` from the current environment."""
    backend = (os.getenv("RAGQA_BACKEND") or "auto").strip().lower()
    if backend not in VALID_BACKENDS:
        backend = "auto"

    api_key = os.getenv("ANTHROPIC_API_KEY") or None
    if api_key is not None and api_key.strip() == "":
        api_key = None

    cfg = Config(
        api_key=api_key,
        model=(os.getenv("RAGQA_MODEL") or "claude-opus-4-8").strip(),
        backend=backend,
        top_k=max(1, _env_int("RAGQA_TOP_K", 4)),
        min_score=_env_float("RAGQA_MIN_SCORE", 0.12),
        max_retries=max(0, _env_int("RAGQA_MAX_RETRIES", 1)),
        chunk_size=max(200, _env_int("RAGQA_CHUNK_SIZE", 900)),
        chunk_overlap=max(0, _env_int("RAGQA_CHUNK_OVERLAP", 150)),
        log_level=(os.getenv("RAGQA_LOG_LEVEL") or "INFO").strip().upper(),
    )
    return cfg

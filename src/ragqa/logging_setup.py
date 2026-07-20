"""Logging configuration.

Logs go to both the console and a rotating file under ``logs/``. Every stage of
the RAG pipeline emits structured log lines so a run can be traced end to end.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False


def configure_logging(level: str = "INFO", log_dir: Path | None = None) -> logging.Logger:
    """Configure the ``ragqa`` logger once and return it.

    Safe to call multiple times; handlers are only attached on the first call.
    """
    global _CONFIGURED
    logger = logging.getLogger("ragqa")

    if _CONFIGURED:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_dir is not None:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_dir / "ragqa.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
            )
            file_handler.setFormatter(fmt)
            logger.addHandler(file_handler)
        except OSError:
            # If we can't write logs to disk, keep going with console only.
            logger.warning("Could not create log directory %s; logging to console only.", log_dir)

    _CONFIGURED = True
    return logger


def get_logger() -> logging.Logger:
    """Return the shared ``ragqa`` logger (configuring a console default if needed)."""
    logger = logging.getLogger("ragqa")
    if not logger.handlers:
        return configure_logging()
    return logger

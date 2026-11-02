"""
Logging configuration for the Music Recommender + AI DJ.

Logs go to the console (warnings and above by default, so normal output stays
readable) and to logs/musicrec.log (everything at INFO and above), so every
step of the AI DJ workflow can be traced after a run.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"


def configure_logging(
    console_level: str = "WARNING", log_dir: Path = DEFAULT_LOG_DIR
) -> logging.Logger:
    """Configure the shared "musicrec" logger once and return it."""
    logger = logging.getLogger("musicrec")
    if logger.handlers:  # already configured (e.g. called twice)
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(getattr(logging, console_level.upper(), logging.WARNING))
    console.setFormatter(fmt)
    logger.addHandler(console)

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "musicrec.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        # If we can't write to disk, keep going with console logging only.
        logger.warning("Could not create log directory %s; console logging only.", log_dir)

    return logger

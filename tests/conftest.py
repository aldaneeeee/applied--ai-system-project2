"""
Shared pytest setup.

The suite always uses the offline backend (or fake clients), so it needs no
API key or network and gives the same results on every machine.
"""

import os
import sys
from pathlib import Path

os.environ["DJ_BACKEND"] = "offline"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402

from src.recommender import load_songs  # noqa: E402


@pytest.fixture(scope="session")
def songs():
    return load_songs(str(PROJECT_ROOT / "data" / "songs.csv"))

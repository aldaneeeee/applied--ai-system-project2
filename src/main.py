"""
Command line runner for the Music Recommender Simulation + AI DJ.

  python -m src.main                         # original Module 3 demo (fixed profile)
  python -m src.main --ask "chill lofi for studying"   # AI DJ: plain-English request
  python -m src.main --ask "..." --trace     # also print each agent step
  python -m src.main --eval                  # run the reliability evaluation
"""

import argparse
import json
import sys
from pathlib import Path

# Support both `python -m src.main` (run from the project root) and
# `python src/main.py` by making the project root importable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.recommender import load_songs, recommend_songs  # noqa: E402
from src.logging_setup import configure_logging  # noqa: E402

try:  # loading .env is a convenience; everything works without it
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

SONGS_CSV = PROJECT_ROOT / "data" / "songs.csv"


def print_recommendations(recommendations) -> None:
    """Print (song, score, reasons) tuples in the original Module 3 format."""
    for rank, (song, score, reasons) in enumerate(recommendations, start=1):
        print(f"\n{rank}. {song['title']}")

        # Artist is optional — only show it if the song has one.
        if song.get("artist"):
            print(f"   Artist: {song['artist']}")

        print(f"   Score:  {score:.2f}")

        # Print each reason on its own line as a bulleted list.
        if reasons:
            print("   Reasons:")
            for reason in reasons:
                print(f"     - {reason}")


def run_classic_demo(songs) -> None:
    """The original Module 3 demo: recommend for a fixed sample profile."""
    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\nTop recommendations for genre=pop, mood=happy, energy=0.8\n")
    print("=" * 50)
    print_recommendations(recommendations)
    print("\n" + "=" * 50)


def run_ai_dj(songs, request: str, k: int, backend: str, show_trace: bool) -> int:
    """Answer a plain-English request with the AI DJ workflow."""
    from src.ai_dj import AIDJ
    from src.llm import LLMError, get_backend

    try:
        dj = AIDJ(songs, backend=get_backend(backend))
    except LLMError as exc:
        print(f"Error: {exc}")
        return 2

    result = dj.run(request, k=k)
    print(f'\nRequest: "{result.request}"')
    if result.status != "ok":
        print(f"\n{result.message}")
    else:
        p = result.profile
        print(f"Interpreted as: genre={p['genre']}, mood={p['mood']}, energy={p['energy']}")
        print("=" * 50)
        print_recommendations(result.recommendations)
        print("\n" + "=" * 50)
        print(f"\nDJ says ({result.explanation_source}): {result.explanation}")
    for warning in result.warnings:
        print(f"Note: {warning}")
    print(f"\n[backend={result.backend} · status={result.status}]")
    if show_trace:
        print("\nAgent trace:")
        for entry in result.trace:
            print("  " + json.dumps(entry, default=str))
    return 0 if result.status == "ok" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Music Recommender + AI DJ")
    parser.add_argument("--ask", metavar="REQUEST", help="describe the music you want in plain English")
    parser.add_argument("-k", type=int, default=5, help="number of songs to recommend (default 5)")
    parser.add_argument("--backend", choices=["auto", "claude", "offline"],
                        help="override DJ_BACKEND (default: auto)")
    parser.add_argument("--trace", action="store_true", help="print each AI DJ step")
    parser.add_argument("--eval", action="store_true", help="run the reliability evaluation")
    args = parser.parse_args(argv)

    configure_logging()
    songs = load_songs(str(SONGS_CSV))
    if not songs:
        print(f"Error: no songs loaded from {SONGS_CSV}. See logs/musicrec.log.")
        return 2

    if args.eval:
        from src.evaluate import main as eval_main
        return eval_main(["--backend", args.backend] if args.backend else [])
    if args.ask is not None:
        return run_ai_dj(songs, args.ask, args.k, args.backend, args.trace)
    run_classic_demo(songs)
    return 0


if __name__ == "__main__":
    sys.exit(main())

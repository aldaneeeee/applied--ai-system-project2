"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

# Support both `python -m src.main` (run from the project root) and
# `python src/main.py` (run with src/ on the path).
try:
    from src.recommender import load_songs, recommend_songs
except ModuleNotFoundError:
    from recommender import load_songs, recommend_songs


def main() -> None:
    """Load songs, recommend for the sample profile, and print the results."""
    songs = load_songs("data/songs.csv")

    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\nTop recommendations for genre=pop, mood=happy, energy=0.8\n")
    print("=" * 50)

    # Each recommendation is a (song, score, reasons) tuple.
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

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()

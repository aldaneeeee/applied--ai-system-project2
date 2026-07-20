import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file into a list of dictionaries.

    Each row becomes one dictionary (one song). Numeric columns are
    converted to int/float so they can be used in calculations later;
    text columns are left as strings.

    Required by src/main.py
    """
    # Columns that should be whole numbers.
    int_fields = {"id", "tempo_bpm"}
    # Columns that should be decimal numbers.
    float_fields = {"energy", "valence", "danceability", "acousticness"}

    songs: List[Dict] = []

    try:
        # newline="" is the recommended way to open files for the csv module.
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)  # uses the header row for dict keys

            for line_num, row in enumerate(reader, start=2):  # header is line 1
                # Convert numeric fields; keep everything else as a string.
                for field in int_fields:
                    if field in row:
                        row[field] = int(row[field])
                for field in float_fields:
                    if field in row:
                        row[field] = float(row[field])
                songs.append(row)

    except FileNotFoundError:
        print(f"Error: could not find the songs file at '{csv_path}'.")
        return []
    except (ValueError, KeyError) as err:
        # A malformed number or missing column would land here.
        print(f"Error: invalid data in '{csv_path}' near line {line_num}: {err}")
        return []

    print(f"Loaded songs: {len(songs)}")
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.

    Scoring recipe:
      +2.0  if the song's genre matches the user's favorite genre
      +1.0  if the song's mood matches the user's favorite mood
      +E    energy similarity, where E = max(0, 1 - abs(song_energy - target))

    Returns:
        (score, reasons) where score is the total numeric score and
        reasons is a list of human-readable explanations.

    Required by recommend_songs() and src/main.py
    """
    # Read preferences flexibly so this works with either the profile-style
    # keys (favorite_genre/favorite_mood/target_energy) or main.py's shorthand
    # keys (genre/mood/energy).
    fav_genre = user_prefs.get("favorite_genre", user_prefs.get("genre"))
    fav_mood = user_prefs.get("favorite_mood", user_prefs.get("mood"))
    target_energy = user_prefs.get("target_energy", user_prefs.get("energy"))

    score = 0.0
    reasons: List[str] = []

    # +1.0 for a genre match (reduced from +2.0 for the Weight Shift test).
    if song.get("genre") == fav_genre:
        score += 1.0
        reasons.append("Genre match (+1.0)")

    # +1.0 for a mood match.
    if song.get("mood") == fav_mood:
        score += 1.0
        reasons.append("Mood match (+1.0)")

    # Energy similarity: closer to the target energy = more points.
    # Base closeness is 0..1; doubled so energy can contribute up to +2.0.
    if target_energy is not None:
        energy_score = 2.0 * max(0.0, 1 - abs(song["energy"] - target_energy))
        score += energy_score
        reasons.append(f"Energy similarity (+{energy_score:.2f})")

    return score, reasons

def recommend_songs(
    user_prefs: Dict, songs: List[Dict], k: int = 5
) -> List[Tuple[Dict, float, List[str]]]:
    """
    Ranks songs for a user and returns the top k recommendations.

    For every song we compute (score, reasons) with score_song(), then
    sort from highest score to lowest and keep the best k. Each returned
    item is a (song, score, reasons) tuple so the score and reasons can
    be displayed to the user later.

    Required by src/main.py
    """
    # Score each song, pairing the song with its score and reasons.
    # score_song() returns (score, reasons), so unpacking it with * gives
    # a clean 3-tuple: (song, score, reasons).
    scored = [(song, *score_song(user_prefs, song)) for song in songs]

    # Sort by score (index 1) from highest to lowest.
    # sorted() builds a NEW list, so the caller's `songs` list is untouched.
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)

    # Return only the top k best matches.
    return ranked[:k]

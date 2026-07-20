# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

### How real-world music recommenders work (the version most people picture)

To most listeners, apps like Spotify, Apple Music, and YouTube Music feel like they "just know" what you want to hear next. Behind that feeling are really three ideas working together:

- **Learning from what you do, not what you say.** Every play, skip, replay, like, and "add to playlist" is a signal. The app watches these behaviors and builds a picture of your taste over time — you never fill out a form describing yourself.
- **"People like you also liked…" (collaborative filtering).** The biggest driver of real recommenders is comparing *you* to *millions of other listeners*. If thousands of people with listening habits similar to yours love a song you haven't heard, the system bets you'll love it too. This is why a brand-new song with no plays is hard to recommend — nobody has reacted to it yet (the "cold-start" problem).
- **Listening to the audio itself (content-based).** Services also analyze the actual sound of a track — its energy, tempo, mood, how acoustic or danceable it is — and recommend songs that *sound similar* to ones you already enjoy. This is the part that works even for obscure songs, because it only needs the audio, not a crowd.

Real systems blend all of this with context (time of day, whether you're working out or winding down) and are tuned to keep you listening. That last point matters: these systems are optimized for **engagement**, which is why they can feel addictive and can quietly narrow what you hear into a comfortable bubble.

### What *this* version prioritizes

This project is a small, transparent **content-based** recommender — deliberately the third idea above, and *only* that one. It does not use crowd data, watch your behavior, or optimize for engagement. Instead it prioritizes:

- **Transparency over accuracy.** Every recommendation comes with a plain-English reason ("recommended because it's chill and matches your energy"). You can always see *why* a song was picked.
- **The song's actual qualities over popularity.** A track is scored on its own attributes, so an unknown song competes fairly with a familiar one. There's no "rich get richer" popularity loop.
- **Matching the user's stated taste over guessing it.** The user *tells* us their preferences up front (a taste profile) rather than us inferring them from surveillance.

Concretely, the design is:

- **`Song`** — each track carries `genre`, `mood`, and four normalized (0–1) audio features: `energy`, `valence`, `danceability`, and `acousticness` (plus `tempo_bpm`).
- **`UserProfile`** — stores the listener's stated taste: `favorite_genre`, `favorite_mood`, a `target_energy` (how energetic they want it), and whether they `likes_acoustic`.
- **Scoring** — for each song the `Recommender` adds up points from several weighted rules: a *closeness* score that rewards songs whose energy is near the user's target (not just high), plus points for a matching genre, a matching mood, and an acoustic preference.
- **Ranking** — every song is scored, then the list is sorted from best to worst, and only the top *k* are shown to the user.

In short: real-world recommenders are big, behavior-driven, and engagement-optimized; this version is small, preference-driven, and built to be **explainable**.

### Comparing each song to the user's taste profile

The recommender treats the user's `UserProfile` as a target and asks, for every song in the catalog, *"how well does this track match what the listener said they want?"* It compares the two piece by piece:

- **Genre** — does the song's `genre` equal the user's `favorite_genre`? (exact match)
- **Mood** — does the song's `mood` equal the user's `favorite_mood`? (exact match)
- **Energy** — how *close* is the song's `energy` to the user's `target_energy`? (a similarity, not a yes/no)

Each comparison earns points, and the points are added up into a single score for that song. A higher score means the song looks more like the listener's stated taste.

### Algorithm Recipe

For each song, start the score at `0` and apply these rules:

| Rule | Points awarded | Type |
|---|---|---|
| Song `genre` equals user's `favorite_genre` | **+2.0** | exact match |
| Song `mood` equals user's `favorite_mood` | **+1.0** | exact match |
| Energy is close to `target_energy` | **similarity points** (up to +1.0) | scaled by closeness |

**Energy similarity** rewards songs whose energy is near the user's target — the closer, the more points. Because energy is normalized to a `0–1` scale, the distance between the song and the target is at most `1.0`, so:

```
energy_points = 1.0 - abs(song_energy - target_energy)
```

- Exact energy match (distance `0`) → **+1.0** (full points)
- Distance of `0.2` → **+0.8**
- Opposite ends of the scale (distance `1.0`) → **+0.0**

This means a song does not have to be a perfect match on energy to earn *some* credit — it simply earns more the closer it gets. Genre remains the heaviest signal (+2.0), mood is secondary (+1.0), and energy fine-tunes the ranking.

### Scoring, sorting, and recommending

1. **Score** every song in the catalog using the recipe above.
2. **Sort** all songs from the highest total score to the lowest.
3. **Recommend** the top *k* songs (the best matches) and show them to the user, each with a plain-English reason for why it was picked.

---

## Potential Biases

Because this recommender is small and rule-based, its scoring choices bake in some biases worth naming:

- **It may over-prioritize genre.** With genre worth +2.0 — double any other single rule — a song that shares the user's favorite genre gets a large head start. This can cause the system to **ignore songs from other genres** that actually share a similar mood or energy and would be great matches. A perfect genre match can outrank a better-rounded song from a different genre.
- **Using only a few features may limit recommendation diversity.** The score looks at just genre, mood, and energy. Rich features already in the dataset — `valence`, `danceability`, `acousticness`, and `tempo_bpm` — are not used, so the recommender can miss meaningful similarities and tends to keep suggesting songs that look alike on those three narrow dimensions instead of surfacing variety.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Running `python -m src.main` with the default **Pop / Happy / energy 0.8** user profile produces:

```
Loaded songs: 18

Top recommendations for genre=pop, mood=happy, energy=0.8

==================================================

1. Sunrise City
   Artist: Neon Echo
   Score:  3.98
   Reasons:
     - Genre match (+2.0)
     - Mood match (+1.0)
     - Energy similarity (+0.98)

2. Gym Hero
   Artist: Max Pulse
   Score:  2.87
   Reasons:
     - Genre match (+2.0)
     - Energy similarity (+0.87)

3. Rooftop Lights
   Artist: Indigo Parade
   Score:  1.96
   Reasons:
     - Mood match (+1.0)
     - Energy similarity (+0.96)

4. Concrete Kings
   Artist: Ravi Stax
   Score:  0.95
   Reasons:
     - Energy similarity (+0.95)

5. Night Drive Loop
   Artist: Neon Echo
   Score:  0.95
   Reasons:
     - Energy similarity (+0.95)

==================================================
```

The top pick, *Sunrise City*, is a full match — it shares the user's genre (pop) and mood (happy) and sits almost exactly at the target energy — so it clearly outscores songs that match on only one or two dimensions.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this




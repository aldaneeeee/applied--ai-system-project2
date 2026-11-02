# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**Mood Catcher 1.0**

It matches songs to your vibe. Simple as that.

**Version 2.0 — Mood Catcher AI DJ.** Adds an AI layer: you can describe what
you want in plain English, and an agentic workflow (Claude, or an offline
keyword parser) turns the request into a taste profile and explains the picks.
Sections 1–9 are the original Module 3 card. Sections 10–14 cover the AI layer.

---

## 2. Intended Use  

**Goal:** VibeMatch suggests songs that fit a listener's taste.

You tell it three things: a favorite genre, a favorite mood, and how much energy you want. It then picks songs that match.

It assumes you know your own taste and can name it. It does not learn from your history.

**Good for:**
- Class projects and learning how recommenders work.
- Playing around with a small song list.
- Seeing *why* a song was picked (it shows its reasons).

**Not intended for:**
- Real apps or real users.
- Big music libraries.
- Any important or high-stakes choice.

This is a classroom tool, not a real product.

---

## 3. How the Model Works  

Think of it like giving each song a score, then picking the winners.

For every song, VibeMatch checks three things:

- **Genre:** Does the song's genre match yours? If yes, it earns points.
- **Mood:** Does the song's mood match yours? If yes, it earns points.
- **Energy:** How close is the song's energy to what you asked for? The closer it is, the more points it gets.

It adds up the points for each song. Then it sorts them from highest to lowest. The top songs are your recommendations.

It also tells you *why* each song was picked, like "genre match" or "energy is close."

**In version 2.0** you don't have to type exact values anymore. The AI DJ reads
a request like "mellow lofi for studying" and fills in genre, mood, and energy
for you. The same scoring rule above still picks the songs. The AI only
translates your words into a profile and explains the result (see section 10).

**What we changed from the starter:** At first a genre match was worth the most. We ran a test and lowered the genre points and raised the energy points. Now energy matters more, and a matching mood counts just as much as a matching genre.

---

## 4. Data  

The model uses one small file of songs.

There are **18 songs** in it. Each song has a title, artist, genre, mood, and some number ratings like energy.

The genres are all over the place. There are 15 different genres, so most genres have just one song. Only pop and lofi have more than one. Moods are the same way, with lots of one-off moods.

Energy is a number from 0 to 1. Our songs run from 0.24 (calmest) up to 0.97 (most intense). Most songs sit on the higher-energy side.

**What's missing:** There are very few calm songs. There is no song for someone who wants super quiet music. And with only 18 songs, whole styles of music just aren't here. So the results can only be as good as this tiny list.

---

## 5. Strengths  

It works well when your taste matches the songs we have.

- **Clear favorites rise to the top.** If a song matches your genre, mood, and energy, it wins. That felt right every time we tested it.
- **Energy matching is solid.** Ask for high energy and you get loud, fast songs. Ask for low energy and you get calm ones.
- **It explains itself.** Every pick comes with a plain reason, so you can see why it showed up.
- **No popularity bias.** A song is judged on its own traits, not on how famous it is. Unknown songs get a fair shot.

It gives the most sensible results for common tastes, like happy pop or high-energy workout music, because we have more of those songs.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

The clearest weakness surfaced during the Weight Shift experiment: our recommendations are driven far more by dataset imbalance than by the scoring weights we chose. The catalog has 18 songs spread across 15 genres, so 13 genres are represented by only a single song, which means the genre match rarely distinguishes one song from another and energy similarity — the only feature that actually varies across all 18 songs — ends up dominating the ranking no matter what weights we set. Because the catalog's energy is also skewed high (it ranges from 0.24 to 0.97 with a cluster between 0.75 and 0.97 and no songs below 0.24), a user who wants very calm music is repeatedly served the same two or three low-energy tracks, producing a filter-bubble effect that comes from the data, not the listener's taste. The scoring also uses exact string matching for genre, so a "pop" user never gets credit for the closely related "indie pop" song *Rooftop Lights*, even though it is arguably a better fit than the "pop" gym track it outranks. In short, the system systematically under-serves users with extreme or unusual preferences and users whose favorite genre happens to be thinly represented in the catalog.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

### User profiles tested

I tested four different "pretend listeners," each standing for a real kind of music taste:

- **Happy Pop** (likes pop, a happy mood, medium-high energy 0.8) — someone who wants upbeat, feel-good songs for everyday listening.
- **High-Energy Fitness** (likes pop, an intense mood, very high energy 0.95) — someone looking for hard-hitting workout music to keep them moving.
- **Calm / Chill** (likes lofi, a chill mood, low energy 0.3) — someone who wants quiet, relaxing background music for studying or winding down.
- **EDM Party** (likes electronic dance music, a euphoric mood, high energy 0.9) — someone in the mood for loud, celebratory dance tracks.

### What the recommender suggested

- **Happy Pop** → *Sunrise City*, *Rooftop Lights*, *Gym Hero*
- **High-Energy Fitness** → *Gym Hero*, *Storm Runner*, *Sunrise City*
- **Calm / Chill** → *Library Rain*, *Midnight Coding*, *Spacewalk Thoughts*
- **EDM Party** → *Neon Pulse Arena*, *Storm Runner*, *Carnival Heat*

Overall the model behaved as expected: calm listeners got calm songs, high-energy listeners got high-energy songs, and each listener's clear favorite ended up on top. The reasons attached to each pick made it easy to see *why* a song was chosen.

### Surprising results

- **The same song can serve two very different people.** *Gym Hero* was the **top** pick for the High-Energy Fitness listener but also appeared (lower down) for the Happy Pop listener. It fits fitness perfectly, but feels a little out of place on a "happy" list because it is actually an *intense* song, not a happy one — it only sneaks in because it is pop and has strong energy.
- **A "less exact" song can beat a perfect-genre song.** For the Happy Pop listener, *Rooftop Lights* (labeled "indie pop") scored **higher** than *Gym Hero* (labeled plain "pop"). That was unexpected, but it makes sense: *Rooftop Lights* matches the happy mood and sits closer to the wanted energy, and those two things together outweigh an exact genre label.
- **A song can be recommended even when its style is completely different.** The EDM Party listener was shown *Storm Runner*, which is a rock song. There simply aren't many electronic songs in the catalog, so the system leaned on energy alone and pulled in a loud rock track that "feels" energetic even though the style is wrong.

### Pairwise comparisons (how two listeners differ and why)

- **Happy Pop vs. High-Energy Fitness:** Both like pop, so both see pop songs — but the fitness listener's list is harder and faster (*Gym Hero*, *Storm Runner*) while the happy listener's is brighter and calmer (*Sunrise City*, *Rooftop Lights*). The difference comes from mood and energy: "intense + 0.95" pulls in aggressive songs, while "happy + 0.8" pulls in cheerful ones.
- **Happy Pop vs. Calm / Chill:** These lists barely overlap. Happy Pop gets bright, medium-fast songs; Calm/Chill gets quiet, slow songs (*Library Rain*, *Midnight Coding*). That is exactly right — one listener asked for energy 0.8 and the other for 0.3, so the system moved them in opposite directions.
- **Happy Pop vs. EDM Party:** Both want upbeat music, but Happy Pop stays in cheerful pop while EDM Party gets loud dance and high-energy tracks. The euphoric mood and electronic taste push the party listener toward bigger, more intense songs.
- **High-Energy Fitness vs. Calm / Chill:** This is the sharpest contrast — one gets the loudest songs in the catalog, the other gets the quietest. Their energy targets (0.95 vs. 0.3) sit at opposite ends, so almost nothing is shared.
- **High-Energy Fitness vs. EDM Party:** Both want high energy, so both lists are fast and loud and even share *Storm Runner*. The difference is flavor: the fitness listener leans on pop workout songs, while the party listener leans toward dance/electronic-style picks.
- **Calm / Chill vs. EDM Party:** Near opposites again. Calm/Chill gets soft lofi and ambient music; EDM Party gets loud dance music. Low energy versus high energy explains the entire gap.

### Why certain songs appear (the key takeaway)

The clearest lesson is that **a listener's stated preferences directly shape what they see**. *Gym Hero* is a great example: it is a pop song with very high energy, so for a **high-energy, fitness-focused** listener it is a near-perfect match and lands at number one. But for a listener who just wants **Happy Pop**, the same song can feel wrong, because its mood is "intense," not "happy" — it only appears on their list thanks to its pop genre and strong energy, not because it truly matches the happy feeling they asked for. This shows the model is mostly doing the right thing (matching energy and genre well), but it can still surface a song that technically scores well while not quite fitting the *mood* a listener had in mind.

---

## 8. Future Work  

If I kept working on it, I would:

1. **Add way more songs.** With only 18, a lot of tastes have nothing to match. A bigger, more balanced list would fix most of the problems.
2. **Let similar genres count.** Right now "pop" and "indie pop" are treated as strangers. I'd give partial credit for close styles so good matches don't get missed.
3. **Push for variety in the top picks.** The list can feel repetitive. I'd make it mix things up a little so you don't get five near-identical songs.

A bonus idea: use the other data we already have, like danceability, to make matches even better.

---

## 9. Personal Reflection  

**My biggest learning moment.** This project showed me that a recommender is really just a scoring rule. It is simpler than I thought. My biggest "aha" was during the weight test: I lowered the genre points and raised the energy points, and the results shifted in a way that made sense. That was the moment it clicked that *I* was in control of the behavior, not some magic box.

**How AI tools helped, and when I checked them.** AI tools sped me up a lot. They helped me write the CSV loader, the scoring function, and clean output without getting stuck on small syntax problems. They also helped me spot the dataset bias I might have missed. But I did not just trust them. I ran the code myself and read the actual recommendations to make sure they were right. One example: the tool assumed a certain way to run the program, but it failed on my setup, so I had to check and fix how the file was started. The lesson was to always run it and see the real output, not just accept that it "should" work.

**What surprised me.** I was surprised that such a simple algorithm can still *feel* like a real recommendation. There is no fancy AI inside, just adding up points and sorting. Yet when it explained "genre match" and "energy is close," it felt smart and personal. It made me realize a lot of what feels like intelligence is really just a clear rule plus a good explanation.

**What I would try next.** If I kept going, I would add many more songs so more tastes have a match. I would let similar genres (like pop and indie pop) share credit. And I would add some variety so the top picks don't all feel the same. I would also like to use the extra data we already have, like danceability, to make the matches even better.

---

# Part 2 — The AI DJ layer (Project 4)

## 10. How the AI DJ Works

The AI DJ is an **agentic workflow**: a fixed sequence of steps where an AI
model fills in some steps, and code checks its work before anything reaches the
user (`src/ai_dj.py`).

| Step | Who does it | What happens |
|---|---|---|
| 1. Validate | code | Reject empty, over-300-character, or letter-less input; strip control characters |
| 2. Interpret | **AI** | Request → `{genre, mood, energy, on_topic}`. Claude must answer in a JSON schema whose genre/mood values are limited to the catalog. If Claude fails, the offline keyword parser takes over. |
| 3. Normalize | code | Drop values not in the catalog, clamp energy to 0–1 (default 0.5), refuse off-topic requests |
| 4. Recommend | original code | `recommend_songs()` scores and ranks every song, unchanged from Module 3 |
| 5. Explain | **AI** | Short explanation built only from the scores and reasons |
| 6. Verify | code | Explanation must name the top pick and **no song that wasn't recommended**; otherwise show the rule-based reasons |

**Backends.** `claude-opus-5-5` through the Anthropic API when `ANTHROPIC_API_KEY`
is set; otherwise a deterministic offline backend (keyword/synonym rules +
template explanation). No model was trained or fine-tuned.

## 11. AI Limitations and Biases

**Limitations**
- **The AI can only be as good as the catalog.** With 18 songs and 15 genres,
  a perfectly understood request often still has no strong match. Example:
  "polka music" has no polka songs, so the picks are ranked by energy alone.
  The system now says so in a note instead of hiding it.
- **Offline parser blind spots (measured).** On 8 "challenge" requests written
  after the keyword rules, the offline backend fully passed only **3/8**. It
  misread negation ("not sad, I want happy songs" → *melancholic*), ignored
  context ("dinner party" → high-energy *euphoric*), and refused "I'm feeling
  blue tonight" and "get hyped" as off-topic, because it has no rule for those
  idioms.
- **First word wins.** In "calm jazz to relax in a coffee shop", "calm" is
  matched before "relax", so the mood becomes *chill*. The one jazz song,
  *Coffee Shop Stories* (mood *relaxed*), then falls to 3rd behind an ambient
  song. Found while testing the web UI.
- **The self-check is narrow.** It catches invented or unrecommended song
  titles, but not other wrong claims an AI explanation might make (for example,
  wrongly calling a song "acoustic").
- **Claude results are not yet measured.** The Claude path is tested with a
  fake client and was checked against the real API only with an invalid key.
  Its accuracy on the eval set is unknown until it is run with a real key.

**Biases**
- **Catalog bias carries straight through.** The AI maps every request onto
  the catalog's 15 genres and 14 moods. A listener whose taste isn't represented
  (K-pop, polka, regional music) is quietly treated as "energy only". Their
  request is understood, but under-served.
- **Vocabulary bias in the offline parser.** It knows the words I listed
  ("hype", "chill", "rap"). Slang, other dialects, or non-English requests
  ("algo tranquilo para estudiar") are under-served or refused as off-topic.
  Who gets good results depends on how they talk.
- **Energy skew.** The catalog leans high-energy (Module 3 finding), so
  calm-music requests keep surfacing the same few songs. The AI layer does not
  fix that.
- **Mood labels are subjective.** Both the catalog's mood labels and the AI's
  reading of words like "blue" or "party" reflect particular cultural
  assumptions about what music fits a feeling.

## 12. Misuse and Prevention

This is a low-stakes app, but the AI layer adds real risks:

| Risk | Prevention in this project |
|---|---|
| **Using the DJ as a general chatbot** ("write my essay", "tell me a joke") | The off-topic check refuses with a fixed message; no free-form AI text reaches the user without passing the self-check |
| **Prompt injection** ("ignore your instructions…") | The request is wrapped in `<request>` tags and both system prompts say it is data, not instructions. Claude's interpretation is constrained to a JSON schema with catalog-only `enum` values. The explanation must pass the title check. Tested offline: the injection challenge case is refused. |
| **Hallucinated recommendations** | Ranking is always done by `score_song()`, never by the AI; explanations that name unrecommended songs are replaced (unit-tested) |
| **Cost / abuse of the API key** | 300-character input limit, `effort: "low"`, 2 SDK retries max, key only read from the environment, `.env` is git-ignored |
| **Over-trust** | Every pick shows its numeric score and reasons; notes say when values were guessed, clamped, or ignored |

## 13. Reliability Observations (real results)

- **Tests:** 39 automated tests pass offline (`pytest`). They include a fake
  Anthropic client covering refusals, truncated output, bad JSON, and network
  errors.
- **Evaluation** (`python -m src.evaluate --backend offline`):
  core **16/16** cases fully passed; challenge **3/8**. Details in README.
- **Honesty about the 100%.** The core cases and the keyword rules were written
  together, so 16/16 mostly shows the rules do what they were designed to do.
  The challenge set was added afterwards and the rules were deliberately **not**
  re-tuned to it. 3/8 is the more honest measure of the offline parser.
- **Failure handling verified for real:** with an invalid API key, the live API
  returned 401 and the workflow fell back to the offline parser and template
  explanation, logging each step, instead of crashing.
- **A bug the new tests exposed in the original code:** the starter
  `Recommender.recommend()` just returned songs in file order. Its test passed
  only because the pop song happened to be listed first. A new test with the
  list reversed proves the finished version really sorts by score.
- **A small inefficiency left in place:** after an authentication failure
  during interpretation, the workflow still attempts the explanation call
  (which fails the same way and falls back). It is harmless and visible in the
  logs.

## 14. AI Collaboration (Project 4)

I built this version with an AI coding assistant (Claude Code), in two steps.
First I asked it only to review my project and propose a plan, without writing
any code. Then I asked it to implement the upgrade end to end. My rules were:
keep my original recommender, don't fabricate any results, run the code and
tests, and tell me what was left for me to do.

**What I asked for and what came back.** The review found something I needed
to know: the top level of my repo held an unrelated RAG app, and my actual
Module 3 recommender was buried in a subfolder "as reference". That didn't meet
the "extend your original project" requirement. So the recommender was moved
back to the root, and the RAG app was archived rather than deleted. On top of
the unchanged scoring engine, the assistant added the AI DJ workflow, the
Claude and offline backends, guardrails, logging, the evaluation, 37 new tests,
the diagram, and the docs.

**One helpful suggestion.** Constrain Claude's answer with a JSON schema whose
genre and mood options come straight from `songs.csv`. Claude can't return a
genre my recommender doesn't know. That turns one of my own Module 3
limitations (exact string matching, "pop" vs. "indie pop") into something the
AI layer handles, without touching my scoring rule.

**One flawed suggestion.** The first evaluation scored a perfect 100%. That
number was misleading, because the keyword rules and the test cases had been
written together, so the test was grading its own answer key. The fix was a
separate set of 8 "challenge" requests written afterwards, with the rules
deliberately left untuned. The honest score was 3/8. It exposed failures on
negation, context, and idioms. Trying requests in the web UI also exposed a
"first word wins" mood bug that the original numbers never showed.

**How the output was checked.** Nothing in the docs is copied from a
prediction. Every output in the README came from a real run: `pytest` (39
passed), `python -m src.evaluate`, the CLI examples, a headless run of the
Streamlit app, a real API call with a deliberately invalid key to prove the
fallback works, and a fresh install built only from the committed files. The
new tests also caught a problem in my original code: the starter
`Recommender.recommend()` never actually sorted, and its test only passed
because the pop song happened to be listed first.

**What is still unverified.** The Claude backend has not been run with a real
API key, so its accuracy on the evaluation is unknown (see section 13).

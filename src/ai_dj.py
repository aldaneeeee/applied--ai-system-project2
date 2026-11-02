"""
AI DJ: an agentic workflow on top of the original Music Recommender.

The listener types what they want in plain English. The AI DJ then runs a
fixed sequence of steps, checking its own work along the way:

  1. validate   - guardrail: reject empty, too-long, or garbled input
  2. interpret  - AI turns the request into a taste profile (genre, mood, energy);
                  if the AI backend fails, fall back to the offline keyword parser
  3. normalize  - guardrail: genre/mood must exist in the catalog, energy is
                  clamped to 0-1; off-topic requests stop here
  4. recommend  - TOOL CALL: the original recommend_songs() scores and ranks songs
  5. explain    - AI writes a friendly explanation of the picks
  6. verify     - self-check: the explanation may only name songs that were
                  actually recommended; otherwise use the rule-based reasons

The recommender (src/recommender.py) still makes every ranking decision. The AI
only handles language in (step 2) and language out (step 5).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .llm import Interpretation, LLMError, OfflineBackend, get_backend, template_explanation
from .recommender import recommend_songs

logger = logging.getLogger("musicrec")

MAX_REQUEST_CHARS = 300
DEFAULT_ENERGY = 0.5
MAX_EXPLANATION_CHARS = 1200

OUT_OF_SCOPE_MESSAGE = (
    "I'm a music DJ, so I can only help with song requests. Try something like "
    "\"upbeat pop for a road trip\" or \"calm lofi for studying\"."
)


@dataclass
class DJResult:
    """Everything the AI DJ produced for one request, including its trace."""
    request: str
    status: str                      # "ok" | "rejected" | "out_of_scope"
    message: str = ""
    profile: Optional[Dict] = None
    recommendations: List[Tuple[Dict, float, List[str]]] = field(default_factory=list)
    explanation: str = ""
    explanation_source: str = ""     # "ai" | "template" | "template-fallback"
    backend: str = ""
    warnings: List[str] = field(default_factory=list)
    trace: List[Dict] = field(default_factory=list)


class AIDJ:
    """Runs the AI DJ workflow over a loaded song catalog."""

    def __init__(self, songs: List[Dict], backend=None):
        if not songs:
            raise ValueError("The song catalog is empty; check data/songs.csv.")
        self.songs = songs
        self.backend = backend if backend is not None else get_backend()
        self._offline = OfflineBackend()
        self.genres = sorted({s["genre"] for s in songs})
        self.moods = sorted({s["mood"] for s in songs})
        self.titles = [s["title"] for s in songs]

    # -- Step 1: input guardrail -------------------------------------------
    @staticmethod
    def validate_request(request) -> Tuple[str, Optional[str]]:
        """Return (cleaned_request, error_message_or_None)."""
        if not isinstance(request, str):
            return "", "Please type your request as text."
        cleaned = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", request)  # drop control chars
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return "", "Please describe the music you want, e.g. \"chill lofi for studying\"."
        if len(cleaned) > MAX_REQUEST_CHARS:
            return cleaned, f"Please keep your request under {MAX_REQUEST_CHARS} characters."
        if not re.search(r"[a-zA-Z]", cleaned):
            return cleaned, "I couldn't find any words in that request."
        return cleaned, None

    # -- Step 3: profile guardrail -----------------------------------------
    def normalize_profile(self, interp: Interpretation) -> Tuple[Dict, List[str]]:
        """Keep only values the recommender can use; record what was changed."""
        warnings = []
        genre = interp.genre.lower().strip() if interp.genre else None
        if genre and genre not in self.genres:
            warnings.append(f"Genre '{genre}' isn't in the catalog, so genre was ignored.")
            genre = None
        mood = interp.mood.lower().strip() if interp.mood else None
        if mood and mood not in self.moods:
            warnings.append(f"Mood '{mood}' isn't in the catalog, so mood was ignored.")
            mood = None
        energy = interp.energy
        if energy is None:
            energy = DEFAULT_ENERGY
            warnings.append(f"No energy level detected; using a neutral {DEFAULT_ENERGY}.")
        elif not 0.0 <= energy <= 1.0:
            clamped = min(1.0, max(0.0, energy))
            warnings.append(f"Energy {energy} was outside 0-1; clamped to {clamped}.")
            energy = clamped
        if genre is None and mood is None:
            warnings.append(
                "I couldn't match a genre or mood from the catalog, so these picks are "
                "ranked by energy only."
            )
        return {"genre": genre, "mood": mood, "energy": round(float(energy), 2)}, warnings

    # -- Step 6: output self-check -----------------------------------------
    def check_explanation(self, text: str, recommendations: List) -> Tuple[bool, str]:
        """An explanation passes only if it names the top pick and no unrecommended songs."""
        if not text or not text.strip():
            return False, "explanation was empty"
        if len(text) > MAX_EXPLANATION_CHARS:
            return False, "explanation was too long"
        lowered = text.lower()
        recommended = {s["title"] for s, _, _ in recommendations}
        mentioned = {t for t in self.titles if t.lower() in lowered}
        invented = mentioned - recommended
        if invented:
            return False, f"mentioned songs that were not recommended: {sorted(invented)}"
        top_title = recommendations[0][0]["title"]
        if top_title not in mentioned:
            return False, f"did not mention the top pick '{top_title}'"
        return True, "explanation only references recommended songs"

    # -- The full workflow --------------------------------------------------
    def run(self, request, k: int = 5) -> DJResult:
        result = DJResult(request=str(request), status="ok", backend=self.backend.name)

        def step(name: str, **details):
            result.trace.append({"step": name, **details})
            logger.info("[%s] %s", name, details)

        # 1. validate
        cleaned, error = self.validate_request(request)
        if error:
            result.status, result.message = "rejected", error
            step("validate", ok=False, reason=error)
            return result
        result.request = cleaned
        step("validate", ok=True, chars=len(cleaned))

        # 2. interpret (AI, with offline fallback)
        source = self.backend.name
        try:
            interp = self.backend.interpret(cleaned, self.genres, self.moods)
        except LLMError as exc:
            logger.warning("Interpretation failed on %s backend: %s", self.backend.name, exc)
            result.warnings.append(f"AI interpretation failed ({exc}); used the offline parser.")
            interp = self._offline.interpret(cleaned, self.genres, self.moods)
            source = "offline-fallback"
        step("interpret", source=source, on_topic=interp.on_topic, genre=interp.genre,
             mood=interp.mood, energy=interp.energy, rationale=interp.rationale)

        # 3. normalize (guardrail)
        if not interp.on_topic:
            result.status, result.message = "out_of_scope", OUT_OF_SCOPE_MESSAGE
            step("normalize", ok=False, reason="request is not about music")
            return result
        profile, warnings = self.normalize_profile(interp)
        result.profile = profile
        result.warnings.extend(warnings)
        step("normalize", ok=True, profile=profile, warnings=warnings)

        # 4. recommend (tool call into the original recommender)
        k = max(1, min(int(k), len(self.songs)))
        recs = recommend_songs(profile, self.songs, k=k)
        result.recommendations = recs
        step("recommend", k=k, top=[(s["title"], round(sc, 2)) for s, sc, _ in recs])

        # 5. explain + 6. verify
        try:
            text = self.backend.explain(cleaned, profile, recs)
            ok, reason = self.check_explanation(text, recs)
        except LLMError as exc:
            text, ok, reason = "", False, f"explanation call failed: {exc}"
        if ok:
            result.explanation = text
            result.explanation_source = "ai" if self.backend.name != "offline" else "template"
        else:
            logger.warning("Explanation rejected (%s); using rule-based reasons.", reason)
            result.warnings.append(f"AI explanation rejected ({reason}); showing rule-based reasons.")
            result.explanation = template_explanation(profile, recs)
            result.explanation_source = "template-fallback"
        step("verify", passed=ok, reason=reason, source=result.explanation_source)
        return result

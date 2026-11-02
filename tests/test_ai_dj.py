"""Tests for the AI DJ workflow: guardrails, fallbacks, and the self-check."""

from src.ai_dj import AIDJ, MAX_REQUEST_CHARS
from src.llm import Interpretation, LLMError, OfflineBackend


class FakeBackend:
    """A stand-in AI backend whose answers each test controls."""

    name = "fake"

    def __init__(self, interpretation=None, explanation=None, fail_interpret=False,
                 fail_explain=False):
        self.interpretation = interpretation
        self.explanation = explanation
        self.fail_interpret = fail_interpret
        self.fail_explain = fail_explain

    def interpret(self, request, genres, moods):
        if self.fail_interpret:
            raise LLMError("simulated API outage")
        return self.interpretation

    def explain(self, request, profile, recommendations):
        if self.fail_explain:
            raise LLMError("simulated API outage")
        if self.explanation is None:
            return f'Start with "{recommendations[0][0]["title"]}".'
        return self.explanation


POP = Interpretation(on_topic=True, genre="pop", mood="happy", energy=0.8)


# --- Input guardrails --------------------------------------------------------
def test_blank_request_is_rejected(songs):
    result = AIDJ(songs, backend=OfflineBackend()).run("   ")
    assert result.status == "rejected"
    assert result.recommendations == []


def test_too_long_request_is_rejected(songs):
    result = AIDJ(songs, backend=OfflineBackend()).run("pop " * MAX_REQUEST_CHARS)
    assert result.status == "rejected"
    assert "characters" in result.message


def test_non_text_and_symbol_only_requests_are_rejected(songs):
    dj = AIDJ(songs, backend=OfflineBackend())
    assert dj.run(None).status == "rejected"
    assert dj.run("!!! ??? 123").status == "rejected"


def test_control_characters_are_stripped(songs):
    result = AIDJ(songs, backend=OfflineBackend()).run("happy\x00 pop\x07 songs")
    assert result.status == "ok"
    assert result.request == "happy pop songs"


def test_off_topic_request_gets_no_recommendations(songs):
    result = AIDJ(songs, backend=OfflineBackend()).run("What's the capital of France?")
    assert result.status == "out_of_scope"
    assert result.recommendations == []


def test_empty_catalog_raises_clear_error():
    import pytest
    with pytest.raises(ValueError):
        AIDJ([], backend=OfflineBackend())


# --- Profile guardrails ------------------------------------------------------
def test_unknown_genre_and_mood_from_ai_are_dropped(songs):
    bad = Interpretation(on_topic=True, genre="k-pop", mood="spooky", energy=0.7)
    result = AIDJ(songs, backend=FakeBackend(bad)).run("k-pop please")
    assert result.status == "ok"
    assert result.profile["genre"] is None and result.profile["mood"] is None
    assert any("k-pop" in w for w in result.warnings)


def test_out_of_range_energy_is_clamped(songs):
    wild = Interpretation(on_topic=True, genre="metal", mood="angry", energy=7.5)
    result = AIDJ(songs, backend=FakeBackend(wild)).run("LOUDEST metal ever")
    assert result.profile["energy"] == 1.0
    assert any("clamped" in w for w in result.warnings)


def test_missing_energy_uses_neutral_default(songs):
    no_energy = Interpretation(on_topic=True, genre="jazz", mood=None, energy=None)
    result = AIDJ(songs, backend=FakeBackend(no_energy)).run("jazz")
    assert result.profile["energy"] == 0.5


# --- The recommender is the tool that ranks songs ----------------------------
def test_recommendations_come_from_original_scoring(songs):
    result = AIDJ(songs, backend=FakeBackend(POP)).run("happy pop", k=3)
    titles = [s["title"] for s, _, _ in result.recommendations]
    assert titles[0] == "Sunrise City"
    assert len(titles) == 3
    scores = [score for _, score, _ in result.recommendations]
    assert scores == sorted(scores, reverse=True)


def test_k_is_bounded_to_catalog_size(songs):
    result = AIDJ(songs, backend=FakeBackend(POP)).run("happy pop", k=500)
    assert len(result.recommendations) == len(songs)


# --- Fallbacks and the explanation self-check --------------------------------
def test_interpretation_failure_falls_back_to_offline_parser(songs):
    result = AIDJ(songs, backend=FakeBackend(fail_interpret=True)).run("chill lofi")
    assert result.status == "ok"
    assert result.profile["genre"] == "lofi"
    assert result.trace[1]["source"] == "offline-fallback"


def test_hallucinated_song_in_explanation_is_caught(songs):
    lie = 'Try "Sunrise City" and also "Bohemian Rhapsody" and "Iron Verdict".'
    result = AIDJ(songs, backend=FakeBackend(POP, explanation=lie)).run("happy pop", k=3)
    # Iron Verdict is in the catalog but was not recommended -> rejected.
    assert result.explanation_source == "template-fallback"
    assert "Sunrise City" in result.explanation
    assert "Iron Verdict" not in result.explanation


def test_explanation_must_mention_top_pick(songs):
    vague = "These songs are great for your mood!"
    result = AIDJ(songs, backend=FakeBackend(POP, explanation=vague)).run("happy pop")
    assert result.explanation_source == "template-fallback"


def test_grounded_ai_explanation_is_kept(songs):
    good = 'Start with "Sunrise City" - it matches your genre, mood, and energy.'
    result = AIDJ(songs, backend=FakeBackend(POP, explanation=good)).run("happy pop")
    assert result.explanation_source == "ai"
    assert result.explanation == good


def test_explanation_failure_falls_back_to_template(songs):
    result = AIDJ(songs, backend=FakeBackend(POP, fail_explain=True)).run("happy pop")
    assert result.status == "ok"
    assert result.explanation_source == "template-fallback"


def test_trace_records_every_step(songs):
    result = AIDJ(songs, backend=OfflineBackend()).run("happy pop")
    assert [t["step"] for t in result.trace] == [
        "validate", "interpret", "normalize", "recommend", "verify"]

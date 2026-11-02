"""Tests for the language backends (offline parser + Claude backend with a fake client)."""

import json
from types import SimpleNamespace

import pytest

from src.llm import ClaudeBackend, LLMError, OfflineBackend, get_backend

GENRES = ["edm", "hip hop", "indie pop", "lofi", "pop", "r&b", "rock"]
MOODS = ["chill", "euphoric", "focused", "happy", "intense", "melancholic"]


# --- Offline keyword parser --------------------------------------------------
@pytest.mark.parametrize("request_text, genre, mood", [
    ("happy pop please", "pop", "happy"),
    ("some indie pop", "indie pop", None),   # longest phrase wins over "pop"
    ("lo-fi beats for studying", "lofi", "focused"),
    ("rap for the gym", "hip hop", "intense"),
    ("rnb", "r&b", None),
])
def test_offline_parser_maps_words_to_catalog(request_text, genre, mood):
    interp = OfflineBackend().interpret(request_text, GENRES, MOODS)
    assert interp.on_topic
    assert (interp.genre, interp.mood) == (genre, mood)


def test_offline_parser_reads_explicit_energy():
    assert OfflineBackend().interpret("pop with energy 0.3", GENRES, MOODS).energy == 0.3


def test_offline_parser_flags_off_topic():
    assert not OfflineBackend().interpret("solve 2x + 3 = 7", GENRES, MOODS).on_topic


# --- Claude backend with a fake Anthropic client -----------------------------
class FakeMessages:
    def __init__(self, text="", stop_reason="end_turn", error=None):
        self.text, self.stop_reason, self.error = text, stop_reason, error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(stop_reason=self.stop_reason,
                               content=[SimpleNamespace(type="text", text=self.text)])


def fake_backend(**kwargs):
    messages = FakeMessages(**kwargs)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return ClaudeBackend(client=client), messages


def test_claude_interpret_parses_structured_output():
    payload = {"on_topic": True, "genre": "lofi", "mood": "chill", "energy": 0.3,
               "rationale": "studying implies calm"}
    backend, messages = fake_backend(text=json.dumps(payload))
    interp = backend.interpret("music to study", GENRES, MOODS)
    assert (interp.genre, interp.mood, interp.energy) == ("lofi", "chill", 0.3)

    sent = messages.calls[0]
    assert sent["model"] == "claude-opus-5-5"
    schema = sent["output_config"]["format"]["schema"]
    assert schema["properties"]["genre"]["enum"] == GENRES + ["none"]
    assert "<request>music to study</request>" in sent["messages"][0]["content"]


def test_claude_none_values_become_missing():
    payload = {"on_topic": True, "genre": "none", "mood": "none", "energy": 0.5,
               "rationale": ""}
    backend, _ = fake_backend(text=json.dumps(payload))
    interp = backend.interpret("anything", GENRES, MOODS)
    assert interp.genre is None and interp.mood is None


def test_claude_bad_json_raises_llm_error():
    backend, _ = fake_backend(text="not json at all")
    with pytest.raises(LLMError):
        backend.interpret("pop", GENRES, MOODS)


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_claude_refusal_or_truncation_raises_llm_error(stop_reason):
    backend, _ = fake_backend(text="{}", stop_reason=stop_reason)
    with pytest.raises(LLMError):
        backend.interpret("pop", GENRES, MOODS)


def test_claude_connection_error_becomes_llm_error():
    import anthropic
    import httpx2
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x"))
    backend, _ = fake_backend(error=error)
    with pytest.raises(LLMError):
        backend.explain("pop", {"genre": "pop", "mood": None, "energy": 0.5}, [])


# --- Backend selection -------------------------------------------------------
def test_get_backend_offline_when_forced():
    assert get_backend("offline").name == "offline"


def test_auto_without_key_uses_offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert get_backend("auto").name == "offline"


def test_forcing_claude_without_key_gives_clear_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        get_backend("claude")

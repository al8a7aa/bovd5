"""F11 NASA-grounded assistant: retrieval, privacy of the prompt, key handling, safety prompt, API gates.
No network: the OpenRouter call is replaced by a fake poster."""
from __future__ import annotations

import json
from typing import Any

import pytest

from astra.features import assistant
from astra.storage import Store

FAKE_KEY = "sk-or-v1-" + "a" * 40


def fake_poster(seen: dict[str, Any]):  # type: ignore[no-untyped-def]
    def post(key: str, payload: dict[str, Any]) -> dict[str, Any]:
        seen["key"], seen["payload"] = key, payload
        return {"model": "test/free-model", "choices": [{"message": {"content": "Stand up slowly after landing [S1]."}}]}
    return post


@pytest.mark.parametrize("question,expected", [
    ("why do I feel dizzy after landing on Mars", "protocol:post_landing_dizziness"),
    ("how much radiation is too much", "hazard:radiation"),
    ("my blood sugar is low before a spacewalk", "protocol:hypoglycemia"),
    ("CO2 headache in the cabin", "guide:cabin_co2"),
    ("what exercise protects my bones", "body:bones"),
])
def test_retrieval_finds_relevant_nasa_sources(question: str, expected: str) -> None:
    assert expected in [d["id"] for d in assistant.retrieve(question)]


def test_prompt_contains_only_question_and_sources(store: Store) -> None:
    assistant.set_key(store, FAKE_KEY, "t")
    seen: dict[str, Any] = {}
    r = assistant.ask(store, "Why do I feel dizzy after landing?", "en", fake_poster(seen))
    msgs = seen["payload"]["messages"]
    text = json.dumps(msgs)
    assert "Name A1" not in text and "A1" not in text  # no names / IDs / readings leave the device
    assert "Never give a diagnosis" in msgs[0]["content"] and "Smart Doctor" in msgs[0]["content"]
    assert "[S1]" in msgs[1]["content"]
    assert seen["payload"]["model"] == assistant.DEFAULT_MODEL
    assert r["grounded"] and r["sources"][0]["n"] == 1 and r["model"] == "test/free-model"


def test_key_is_encrypted_and_never_in_blackbox(store: Store) -> None:
    assistant.set_key(store, FAKE_KEY, "t")
    raw = json.dumps([dict(x) for x in store.q("SELECT * FROM settings")])
    assert FAKE_KEY not in raw
    assert assistant.get_key(store) == FAKE_KEY
    assert FAKE_KEY not in json.dumps([dict(x) for x in store.q("SELECT * FROM blackbox")])
    assert assistant.status(store)["configured"] is True and "key" not in assistant.status(store)
    assistant.set_key(store, None, "t")
    assert assistant.get_key(store) is None


def test_errors_are_clear(store: Store) -> None:
    with pytest.raises(assistant.AssistantError, match="not set up"):
        assistant.ask(store, "Why do I feel dizzy?", "en", fake_poster({}))
    with pytest.raises(assistant.AssistantError):
        assistant.set_key(store, "not a key!", "t")
    assistant.set_key(store, FAKE_KEY, "t")
    with pytest.raises(assistant.AssistantError, match="3–500"):
        assistant.ask(store, "hi", "en", fake_poster({}))


def test_api_gates(client, app) -> None:  # type: ignore[no-untyped-def]
    assert client("astro1").post("/api/assistant/key", {"key": FAKE_KEY})[0] == 403  # only flight surgeon
    st, s = client("astro1").get("/api/assistant/status")
    assert st == 200 and "key" not in s
    st, r = client("astro1").post("/api/assistant/ask", {"question": "Why do I feel dizzy after landing?"})
    assert st == 403 and "consent" in r["error"]  # astronaut must opt in first
    st, s = client("surgeon1").post("/api/assistant/key", {"key": FAKE_KEY, "model": "openrouter/free"})
    assert st == 200 and s["configured"] and FAKE_KEY not in json.dumps(s)
    client("surgeon1").post("/api/assistant/key", {"key": None})

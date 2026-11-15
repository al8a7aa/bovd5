"""
F11 · NASA-GROUNDED RESEARCH ASSISTANT (EXPERIMENTAL, online, opt-in)
====================================================================
Answers astronauts' questions in plain language, using ONLY the NASA / CSA
knowledge bundled with the app (retrieval-augmented generation):

  question → local keyword retrieval over config/guidance.json, body regions and
  hazards, Smart Doctor protocols, the evidence register, thresholds and the
  reference list → top excerpts → OpenRouter chat model (free model by default)
  → answer that cites the excerpts as [S1], [S2] …

Safety and privacy (ISO 14971 risk R-12 "misuse of CDSS", ISO/IEC 23894):
  * It never changes the rule-based Smart Doctor protocols, thresholds or alerts;
    it only explains. The system prompt forbids diagnoses, drug names and doses
    and sends the user to the matching Smart Doctor protocol and the CMO.
  * Only the typed question and the knowledge excerpts leave the device – never
    readings, names or astronaut IDs. Off until an OpenRouter key is set, and
    astronauts must grant the 'ai_assistant' consent first.
  * The API key is stored encrypted (AES-256-GCM) in the local database or read
    from the OPENROUTER_API_KEY environment variable; it is never sent to the
    browser or written to the black box.
  * Needs internet. Without it the rest of the app – including Smart Doctor –
    keeps working offline.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from functools import cache
from typing import Any

from .. import config
from ..storage import Store

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"  # OpenRouter's router across currently free models
KEY_SETTING = "ai.openrouter_key_enc"
MODEL_SETTING = "ai.model"
TOP_K = 6
TIMEOUT_S = 45

_STOP = set("""a an and are as at be but by can do does for from has have how i if in into is it its me my
not of on or so that the their them then there these this to was what when where which who why will with
you your should would could about after before during than also any all more most very much too many feel get got
cannot can't dont don't need want know tell please""".split())


class AssistantError(RuntimeError):
    """Configuration or network problem, shown to the user as-is."""


# ------------------------------------------------------------------ knowledge base
@cache
def knowledge() -> list[dict[str, Any]]:
    """Documents built from the bundled NASA/CSA material. Each has id, title, text, citation keys."""
    docs: list[dict[str, Any]] = []
    th = config.thresholds()["indicators"]
    for k, g in config.load("guidance")["indicators"].items():
        label = th.get(k, {}).get("label_en", k)
        docs.append({"id": f"guide:{k}", "title": f"{label} – why it matters and how to stay healthy",
                     "text": g["why_en"] + " Prevention: " + " ".join(g["improve_en"]), "cite": g["citation"]})
    for k, ind in th.items():
        rules = "; ".join(f"red if {next(iter(r))} {next(iter(r.values()))}" for r in ind.get("red_if", []))
        rules += "; " + "; ".join(f"yellow if {next(iter(r))} {next(iter(r.values()))}" for r in ind.get("yellow_if", []))
        docs.append({"id": f"threshold:{k}", "title": f"{ind['label_en']} – app thresholds ({ind['unit']})",
                     "text": f"{ind['label_en']} in {ind['unit']}: {rules.strip('; ')}. Thresholds need flight-surgeon review.",
                     "cite": ind.get("citation", [])})
    regions = config.load("body_regions")
    for k, r in regions["regions"].items():
        docs.append({"id": f"body:{k}", "title": f"{r['en']} – function and spaceflight effects",
                     "text": f"Function: {r['function_en']} In space: {r['micro_en']}", "cite": r.get("citation", [])})
    for k, h in regions["hazards"].items():
        docs.append({"id": f"hazard:{k}", "title": f"NASA hazard: {h['en']}",
                     "text": f"{h['en']}. " + str(h.get("desc_en", h.get("text_en", ""))), "cite": ["hrp_hazards"]})
    for pid, p in config.protocols()["protocols"].items():
        steps = " ".join(n.get("en", "") for n in p["nodes"].values())
        docs.append({"id": f"protocol:{pid}", "title": f"Smart Doctor protocol: {p['title_en']}",
                     "text": steps, "cite": p.get("citation", [])})
    ev = config.load("evidence")
    items = ev if isinstance(ev, list) else next((v for v in ev.values() if isinstance(v, list)), [])
    for e in items:
        docs.append({"id": f"evidence:{e['id']}", "title": f"Evidence {e['id']}: {e.get('indicator_en', '')}",
                     "text": f"{e.get('indicator_en', '')}: {e.get('value', '')} {e.get('unit', '')}. "
                             f"Source: {e.get('title', '')}, {e.get('organization', '')} ({e.get('date', '')}).",
                     "url": e.get("url", ""), "cite": []})
    for k, r in config.references().items():
        if k != "clinical_default":
            docs.append({"id": f"ref:{k}", "title": r["apa"], "text": r["apa"], "url": r.get("url", ""), "cite": [k]})
    for d in docs:
        d["_tokens"] = _tokens(d["title"] + " " + d["text"])
    return docs


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower().replace("co₂", "co2"))
    return [w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w  # crude plural folding
            for w in words if len(w) > 2 and w not in _STOP]


@cache
def _idf() -> dict[str, float]:
    docs = knowledge()
    df: dict[str, int] = {}
    for d in docs:
        for w in set(d["_tokens"]):
            df[w] = df.get(w, 0) + 1
    return {w: math.log(1 + len(docs) / n) for w, n in df.items()}


def retrieve(question: str, k: int = TOP_K) -> list[dict[str, Any]]:
    """Top-k knowledge documents for a question (simple TF-IDF overlap, fully offline)."""
    q = set(_tokens(question))
    idf = _idf()
    scored = []
    for d in knowledge():
        toks = set(d["_tokens"])
        s = sum(idf.get(w, 0.0) for w in q & toks) / (1 + len(toks)) ** 0.25  # mild length normalisation
        if s > 0:
            scored.append((s, d))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:k]]


# ------------------------------------------------------------------ key + model
def get_key(store: Store) -> str | None:
    env = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if env:
        return env
    tok = store.get_setting(KEY_SETTING)
    return store.cipher.decrypt(tok).decode("utf-8") if tok else None


def set_key(store: Store, key: str | None, actor: str) -> None:
    """Store the key encrypted. Written directly (not via set_setting) so it never reaches the black box."""
    if key:
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z0-9_\-:.]{20,200}", key):
            raise AssistantError("That does not look like an OpenRouter API key.")
        store.x("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (KEY_SETTING, json.dumps(store.cipher.encrypt(key.encode()))))
    else:
        store.x("DELETE FROM settings WHERE key=?", (KEY_SETTING,))
    store.bb_append(actor, "setting", {"key": "ai.openrouter_key", "value": "[set]" if key else "[removed]"})


def model(store: Store) -> str:
    return str(store.get_setting(MODEL_SETTING) or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL)


def status(store: Store) -> dict[str, Any]:
    return {"configured": bool(get_key(store)), "from_env": bool(os.environ.get("OPENROUTER_API_KEY")),
            "model": model(store), "provider": "OpenRouter", "documents": len(knowledge())}


# ------------------------------------------------------------------ ask
SYSTEM = """You are the BÖVD research assistant for astronauts on space missions.
Rules you must follow:
1. Answer ONLY from the numbered NASA/CSA sources given to you. If they do not cover the question, say so plainly.
2. Cite the sources you use as [S1], [S2] … right after the sentence they support.
3. Never give a diagnosis, never name medicines or doses, never contradict the app's protocols.
4. For any symptom, illness or red/yellow result: tell the astronaut to open the matching Smart Doctor protocol and contact the Crew Medical Officer.
5. Use short, simple sentences for a non-doctor. Maximum 150 words. Answer in {lang}."""


def build_messages(question: str, docs: list[dict[str, Any]], lang: str) -> list[dict[str, str]]:
    src = "\n\n".join(f"[S{i + 1}] {d['title']}\n{d['text']}" for i, d in enumerate(docs))
    return [{"role": "system", "content": SYSTEM.format(lang="Arabic" if lang == "ar" else "English")},
            {"role": "user", "content": f"Sources:\n{src}\n\nAstronaut's question: {question}"}]


def _post(key: str, payload: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover - network
    req = urllib.request.Request(OPENROUTER_URL, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "BOVD"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310 - fixed https URL
            return dict(json.loads(r.read().decode("utf-8")))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            raise AssistantError("OpenRouter rejected the API key (401). Check the key in the assistant settings.") from e
        if e.code == 429:
            raise AssistantError("The free model is busy or the daily free limit is reached (429). Try again later.") from e
        raise AssistantError(f"OpenRouter error {e.code}: {detail}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise AssistantError("No internet connection to OpenRouter. The assistant needs internet; "
                             "Smart Doctor protocols still work offline.") from e


def ask(store: Store, question: str, lang: str = "en", poster: Any = None) -> dict[str, Any]:
    question = (question or "").strip()
    if not 3 <= len(question) <= 500:
        raise AssistantError("Please type a question of 3–500 characters.")
    key = get_key(store)
    if not key:
        raise AssistantError("The AI assistant is not set up yet: a flight surgeon must add an OpenRouter API key.")
    docs = retrieve(question)
    if not docs:
        return {"answer": "The bundled NASA/CSA sources do not cover this question. Ask your Crew Medical Officer.",
                "sources": [], "model": None, "grounded": False}
    payload = {"model": model(store), "messages": build_messages(question, docs, lang), "temperature": 0.2, "max_tokens": 400}
    res = (poster or _post)(key, payload)
    try:
        answer = str(res["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise AssistantError("The model returned an empty answer. Try again.") from e
    sources = [{"n": i + 1, "id": d["id"], "title": d["title"], "url": d.get("url", ""),
                "citations": config.cite(d.get("cite", []))} for i, d in enumerate(docs)]
    store.bb_append("assistant", "ai_query", {"model": res.get("model", payload["model"]), "sources": [d["id"] for d in docs]})
    return {"answer": answer, "sources": sources, "model": res.get("model", payload["model"]), "grounded": True,
            "disclaimer": "AI-generated from the NASA/CSA sources listed – EXPERIMENTAL, not medical advice. "
                          "Follow Smart Doctor protocols and your Crew Medical Officer."}

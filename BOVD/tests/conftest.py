"""Shared pytest fixtures (IEC 62304 §5.5 unit verification; ISO/IEC/IEEE 29119)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from astra import auth
from astra.server import App
from astra.storage import Store


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "db" / "t.sqlite", key=os.urandom(32))
    for aid in ("A1", "A2"):
        s.add_astronaut(aid, f"Name {aid}", f"P{aid}")
    s.set_setting("gravity_context", "iss")
    return s


def grant_all(store: Store, aid: str) -> None:
    for c in ("voice_features", "vision", "crew_interaction", "radiation", "urine", "connection",
              "research_export", "webcam_blink"):
        store.set_consent(aid, c, True, "test")


@pytest.fixture(scope="session")
def app(tmp_path_factory: pytest.TempPathFactory) -> App:
    return App(tmp_path_factory.mktemp("app"), seed=True)


class Client:
    def __init__(self, app: App, user: str | None = None) -> None:
        self.app = app
        self.h: dict[str, str] = {}
        if user:
            st, _, b = app.dispatch("POST", "/api/login", {}, json.dumps({"username": user, "password": "astra2026"}).encode())
            assert st == 200, b
            self.h = {"authorization": "Bearer " + json.loads(b)["token"]}

    def get(self, path: str) -> tuple[int, Any]:
        st, ct, b = self.app.dispatch("GET", path, self.h, b"")
        return st, json.loads(b) if "json" in ct else b

    def post(self, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        st, ct, b = self.app.dispatch("POST", path, self.h, json.dumps(body or {}).encode())
        return st, json.loads(b) if "json" in ct else b


@pytest.fixture()
def client(app: App):  # type: ignore[no-untyped-def]
    return lambda user=None: Client(app, user)


__all__ = ["grant_all", "auth"]

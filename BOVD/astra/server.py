"""
BÖVD · local HTTP server (REST API + static HTML UI)
============================================================
Python standard library only (http.server). Binds to 127.0.0.1 so the app is
reachable ONLY from this computer – nothing leaves the machine (offline-first,
on-device processing; no cloud).

Real-time updates: the UI polls ``/api/poll`` every 3 s (replaces WebSocket so
that no third-party package is needed). An internal thread runs
``alerts.tick`` every 5 s (repeat / escalate / deliver delayed messages).

OpenAPI 3 description: GET /api/openapi.json (generated from the route table).

Standards alignment (designed in alignment with, not certified):
  ISO/IEC 27002 §8.5 secure authentication, §8.20 network security (loopback
  only), §8.15 logging (black box); IEC 62304 §5.3 (api layer separated).
"""
from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import alerts, auth, config, crypto, engine, fhir, physio, service, synthetic, validation
from .pose import session as pose
from .config import DATA_DIR, DB_DIR, WEB_DIR
from .consent import ConsentError, is_enabled, require
from .features import assistant, blackbox, cdss, coach, connection, crew, radiation, urine, vision, voice
from .storage import Store

VERSION = "0.9.0-hackathon"
DEMO_PASSWORD = "astra2026"  # noqa: S105 - demo-only accounts, documented in README/PRIVACY
Handler = Callable[["Ctx"], Any]
ROUTES: list[tuple[str, re.Pattern[str], Handler, str | None, str]] = []


def route(method: str, path: str, perm: str | None = "auth", doc: str = "") -> Callable[[Handler], Handler]:
    """Register a handler. perm=None → public, 'auth' → any logged-in user."""
    def deco(fn: Handler) -> Handler:
        pat = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "$")
        ROUTES.append((method, pat, fn, perm, doc or (fn.__doc__ or "").strip().split("\n")[0]))
        return fn
    return deco


class ApiError(Exception):
    def __init__(self, status: int, msg: str) -> None:
        super().__init__(msg)
        self.status = status


class Ctx:
    """Request context passed to handlers."""

    def __init__(self, app: App, method: str, path: str, query: dict[str, list[str]], body: Any,
                 claims: dict[str, Any] | None, params: dict[str, str]) -> None:
        self.app, self.method, self.path, self.query, self.body = app, method, path, query, body
        self.claims, self.params = claims, params

    @property
    def store(self) -> Store:
        return self.app.store

    @property
    def user(self) -> str:
        return str(self.claims["sub"]) if self.claims else "anonymous"

    @property
    def role(self) -> str:
        return str(self.claims["role"]) if self.claims else ""

    def arg(self, name: str, default: str | None = None) -> str | None:
        v = self.query.get(name)
        return v[0] if v else default

    def b(self, name: str, default: Any = None) -> Any:
        return (self.body or {}).get(name, default) if isinstance(self.body, dict) else default

    def aid(self, behavioral: bool = False, write: bool = False) -> str:
        """Target astronaut id + object-level access check."""
        aid = self.b("aid") or self.arg("aid") or (self.claims or {}).get("aid")
        if not aid:
            raise ApiError(400, "aid required")
        if not self.claims:
            raise ApiError(401, "login required")
        if write and self.role in ("researcher", "bhs") and not behavioral:
            raise ApiError(403, "role cannot write health data")
        if not auth.can_read_astronaut(self.claims, str(aid), behavioral):
            raise ApiError(403, "not allowed for this astronaut")
        return str(aid)


class App:
    def __init__(self, data_dir: Path | None = None, seed: bool = True, quick_seed: bool = False) -> None:
        db_dir = (data_dir / "db") if data_dir else DB_DIR
        self.store = Store(db_dir / "astra.sqlite")
        secret_path = db_dir / "jwt.secret"
        if not secret_path.exists():
            secret_path.write_bytes(os.urandom(32))
        self.secret = secret_path.read_bytes()
        self.pseudo_secret = crypto.load_or_create_key(db_dir / "pseudonym.key")
        if seed and not self.store.users():
            seed_demo(self.store, quick=quick_seed)

    def dispatch(self, method: str, raw_path: str, headers: dict[str, str], body: bytes) -> tuple[int, str, bytes]:
        url = urlparse(raw_path)
        q = parse_qs(url.query)
        tok = headers.get("authorization", "").removeprefix("Bearer ").strip() or (q.get("token") or [""])[0]
        claims = auth.read_token(self.secret, tok) if tok else None
        for m, pat, fn, perm, _ in ROUTES:
            mt = pat.match(url.path)
            if m != method or not mt:
                continue
            try:
                if perm is not None and claims is None:
                    raise ApiError(401, "login required")
                if perm not in (None, "auth") and not auth.can(str(claims["role"]), perm):  # type: ignore[index]
                    raise ApiError(403, f"permission '{perm}' required")
                data = json.loads(body.decode("utf-8")) if body else {}
                res = fn(Ctx(self, method, url.path, q, data, claims, mt.groupdict()))
                if isinstance(res, tuple):  # (content-type, bytes)
                    return 200, res[0], res[1]
                return 200, "application/json", json.dumps(res, ensure_ascii=False, default=str).encode()
            except ApiError as e:
                return e.status, "application/json", json.dumps({"error": str(e)}).encode()
            except ConsentError as e:
                return 403, "application/json", json.dumps({"error": f"consent/feature gate: {e}"}).encode()
            except (ValueError, KeyError) as e:
                return 400, "application/json", json.dumps({"error": f"{type(e).__name__}: {e}"}).encode()
            except Exception as e:  # pragma: no cover
                traceback.print_exc()
                return 500, "application/json", json.dumps({"error": str(e)}).encode()
        return 404, "application/json", b'{"error":"not found"}'


# =============================================================== seeding
DEMO_CREW = [("A1", "Noor Al-Harthi", "Falcon"), ("A2", "Sami Rahman (CMO)", "Comet"),
             ("A3", "Lina Haddad", "Nova"), ("A4", "Omar Khalid", "Orbit")]
DEMO_USERS = [("astro1", "astronaut", "Noor (astronaut)", "A1"), ("astro3", "astronaut", "Lina (astronaut)", "A3"),
              ("cmo1", "cmo", "Sami (Crew Medical Officer)", "A2"), ("bhs1", "bhs", "Behavioral health specialist", None),
              ("surgeon1", "flight_surgeon", "Ground flight surgeon", None), ("research1", "researcher", "Researcher", None)]
DEMO_SCEN = {"A1": "normal_0g", "A2": "normal_0g", "A3": "sleep_debt", "A4": "rising_calcium"}


def seed_demo(store: Store, quick: bool = False) -> None:
    print("[BÖVD] First start: creating demo crew and SYNTHETIC data …", flush=True)
    for aid, name, ps in DEMO_CREW:
        store.add_astronaut(aid, name, ps)
    for u, role, disp, uaid in DEMO_USERS:
        salt, h = auth.hash_password(DEMO_PASSWORD)
        store.add_user(u, role, disp, uaid, salt, h)
    store.set_setting("gravity_context", "iss")
    for aid, *_ in DEMO_CREW:
        print(f"[BÖVD]   scenario {DEMO_SCEN[aid]} for {aid}", flush=True)
        synthetic.generate(store, aid, DEMO_SCEN[aid], days=8 if quick else 14)
        store.set_consent(aid, "webcam_blink", False, "seed")
    store.set_consent("A4", "research_export", False, "seed")
    n = seed_real(store)
    if n:
        print(f"[BÖVD]   REAL data: {n} observations from NASA OSDR OSD-575 (Inspiration4)", flush=True)
    print("[BÖVD] Seed complete.", flush=True)


REAL_BUNDLES = [config.ROOT / "data" / "real" / "OSD-575" / "OSD-575_glucose.fhir.json"]


def seed_real(store: Store) -> int:
    """Load the bundled REAL NASA OSDR data (built by scripts/build_osd575.py), if present."""
    n = 0
    for path in REAL_BUNDLES:
        if not path.exists():
            continue
        bundle = json.loads(path.read_text(encoding="utf-8"))
        for e in bundle.get("entry", []):
            r = e["resource"]
            aid = r["subject"]["reference"].split("/", 1)[1]
            crew = aid.rsplit("-", 1)[-1]
            store.add_astronaut(aid, f"Inspiration4 {crew} (REAL, OSD-575)", f"I4-{crew}")
            store.add_observation(r, "osdr-loader")
            n += 1
    return n


# =============================================================== routes
@route("GET", "/api/health", None)
def r_health(c: Ctx) -> Any:
    """Liveness + crypto backend."""
    return {"ok": True, "version": VERSION, "crypto": crypto.BACKEND, "time": fhir.now_iso()}


@route("POST", "/api/login", None)
def r_login(c: Ctx) -> Any:
    """Log in → JWT."""
    u = c.store.user(str(c.b("username", "")))
    if not u or not auth.verify_password(str(c.b("password", "")), u["salt"], u["pw_hash"]):
        c.store.bb_append(str(c.b("username", "?")), "login.fail", {})
        raise ApiError(401, "wrong username or password")
    c.store.bb_append(u["username"], "login", {"role": u["role"]})
    return {"token": auth.make_token(c.app.secret, u), "user": {k: u[k] for k in ("username", "role", "display", "astronaut_id")}}


@route("GET", "/api/demo-users", None)
def r_demo_users(c: Ctx) -> Any:
    """Demo accounts (prototype only)."""
    return {"password": DEMO_PASSWORD, "users": c.store.users()}


@route("GET", "/api/meta", None)
def r_meta(c: Ctx) -> Any:
    """All configuration the UI needs (indicators, contexts, references …)."""
    return {"version": VERSION, "indicators": config.thresholds()["indicators"], "thresholds": config.thresholds(),
            "gravity": config.gravity(), "references": config.references(), "features": config.features(),
            "regions": config.load("body_regions"), "scenarios": synthetic.SCENARIOS,
            "protocols": cdss.list_protocols(), "standards": config.load("standards"),
            "status": config.load("project_status"), "routine": service.DEFAULT_ROUTINE,
            "conditions": validation.REQUIRED_CONDITIONS, "crypto": crypto.BACKEND, "cabin_preset": c.store.get_setting("cabin_preset", "iss"),
            "flags_effective": {f: is_enabled(c.store, f) for f in config.features()["flags"]}}


@route("GET", "/api/me")
def r_me(c: Ctx) -> Any:
    """Current user."""
    return {"user": next((u for u in c.store.users() if u["username"] == c.user), None)}


@route("GET", "/api/crew")
def r_crew(c: Ctx) -> Any:
    """Crew list (filtered by role)."""
    crew_ = c.store.astronauts()
    if c.role == "astronaut":
        crew_ = [a for a in crew_ if a["id"] == c.claims["aid"]]  # type: ignore[index]
    if c.role == "researcher":
        crew_ = []
    return {"crew": [{"id": a["id"], "name": a["name"] if c.role != "researcher" else a["pseudonym"],
                      "pseudonym": a["pseudonym"]} for a in crew_]}


@route("GET", "/api/dashboard")
def r_dash(c: Ctx) -> Any:
    """Dashboard: status ring, composite score, body regions, alerts."""
    return service.dashboard(c.store, c.aid())


@route("GET", "/api/series")
def r_series(c: Ctx) -> Any:
    """Time series with baseline band + gravity-transition markers."""
    d = c.arg("days")
    return service.series(c.store, c.aid(), str(c.arg("indicator")), float(d) if d else None)


@route("POST", "/api/validate")
def r_validate(c: Ctx) -> Any:
    """Dry-run validation (no storage)."""
    return validation.validate(str(c.b("indicator")), c.b("value"), c.b("unit"), c.b("conditions")).as_dict()


@route("POST", "/api/readings")
def r_readings(c: Ctx) -> Any:
    """Submit readings → validation → assessment → alert."""
    aid = c.aid(write=True)
    cond = c.b("conditions") or {}
    out = []
    items = list(c.b("readings") or [])
    sy = next((r for r in items if r["indicator"] == "systolic"), None)
    di = next((r for r in items if r["indicator"] == "diastolic"), None)
    if sy and di:
        s, d = validation.validate_bp(sy["value"], di["value"], cond)
        if not (s.ok and d.ok):
            return {"results": [{"ok": False, "validation": s.as_dict()}, {"ok": False, "validation": d.as_dict()}]}
    for r in items:
        if r.get("value") in (None, ""):
            continue
        out.append(service.record(c.store, c.user, aid, r["indicator"], r["value"], r.get("unit"), cond))
    return {"results": out}


@route("POST", "/api/stand_test")
def r_stand(c: Ctx) -> Any:
    """Post-landing seated→stand test."""
    aid = c.aid(write=True)
    return service.record_stand_test(c.store, c.user, aid, float(c.b("seated_hr")), float(c.b("seated_sys")),
                                     float(c.b("stand_hr")), float(c.b("stand_sys")))


@route("GET", "/api/alerts")
def r_alerts(c: Ctx) -> Any:
    """Alerts visible to this user."""
    st = c.arg("status")
    al = c.store.alerts(status=st)
    if c.role == "astronaut":
        al = [a for a in al if a["astronaut_id"] == c.claims["aid"]]  # type: ignore[index]
    elif c.role in ("researcher", "bhs"):
        al = []
    if c.role == "flight_surgeon":  # ground sees only what has ARRIVED through the delayed link
        arrived = {m["body"].get("alert_id") for m in c.store.queue("down") if m["delivered"]}
        al = [a for a in al if a["id"] in arrived]
    return {"alerts": al, "tiers": alerts.TIERS, "policy": alerts.POLICY}


@route("POST", "/api/alerts/{id}/ack")
def r_ack(c: Ctx) -> Any:
    """Acknowledge an alert (ground acks travel with comm delay)."""
    a = next((x for x in c.store.alerts() if x["id"] == c.params["id"]), None)
    if not a:
        raise ApiError(404, "alert not found")
    if not (auth.can(c.role, "ack_any") or (auth.can(c.role, "ack_own") and a["astronaut_id"] == c.claims["aid"])):  # type: ignore[index]
        raise ApiError(403, "cannot acknowledge this alert")
    return alerts.acknowledge(c.store, a["id"], {"username": c.user, "role": c.role})


@route("GET", "/api/poll")
def r_poll(c: Ctx) -> Any:
    """Lightweight poll: counts + SPE + delay (replaces WebSocket)."""
    act = c.store.alerts(status="active")
    if c.role == "astronaut":
        act = [a for a in act if a["astronaut_id"] == c.claims["aid"]]  # type: ignore[index]
    if c.role in ("researcher", "bhs"):
        act = []
    if c.role == "flight_surgeon":  # ground: only alerts that have arrived over the delayed link
        arrived = {m["body"].get("alert_id") for m in c.store.queue("down") if m["delivered"]}
        act = [a for a in act if a["id"] in arrived]
    return {"active": len(act), "high": sum(a["priority"] == "high" for a in act),
            "medium": sum(a["priority"] == "medium" for a in act), "spe": c.store.get_setting("spe"),
            "delay_s": alerts.current_delay_s(c.store), "gravity": c.store.get_setting("gravity_context", "iss"),
            "time": fhir.now_iso(), "gtp": service.gtp_status(c.store)}


@route("GET", "/api/queue")
def r_queue(c: Ctx) -> Any:
    """Store-and-forward queue (Earth ↔ spacecraft)."""
    if c.role in ("researcher", "bhs", "astronaut"):
        raise ApiError(403, "CMO or flight surgeon only")
    q = c.store.queue()
    if c.role == "flight_surgeon":
        q = [m for m in q if m["delivered"] or m["direction"] == "up"]
    return {"queue": q, "delay_s": alerts.current_delay_s(c.store)}


@route("POST", "/api/tick")
def r_tick(c: Ctx) -> Any:
    return alerts.tick(c.store)


@route("POST", "/api/gravity")
def r_gravity(c: Ctx) -> Any:
    """Switch gravity context (rule 7)."""
    if c.role in ("researcher", "bhs"):
        raise ApiError(403, "not allowed")
    return service.set_gravity(c.store, str(c.b("context")), c.user)


@route("POST", "/api/delay")
def r_delay(c: Ctx) -> Any:
    """Override one-way comm delay (seconds) for demos; null = context default."""
    if c.role in ("researcher", "bhs"):
        raise ApiError(403, "not allowed")
    v = c.b("seconds")
    c.store.set_setting("delay_s_override", None if v in (None, "") else float(v), c.user)
    return {"delay_s": alerts.current_delay_s(c.store)}


@route("GET", "/api/events")
def r_events(c: Ctx) -> Any:
    return {"events": c.store.events()}


@route("POST", "/api/events")
def r_add_event(c: Ctx) -> Any:
    """Mission timeline event (landing/return triggers the Gravity Transition Protocol)."""
    if c.role in ("researcher", "bhs"):
        raise ApiError(403, "not allowed")
    return service.add_event(c.store, str(c.b("type")), str(c.b("context", "iss")), str(c.b("note", "")), c.user,
                             c.b("ts"))


@route("POST", "/api/gtp/step")
def r_gtp_step(c: Ctx) -> Any:
    g = c.store.get_setting("gtp")
    if not g:
        raise ApiError(404, "no active protocol")
    g["done"][int(c.b("index"))] = bool(c.b("done"))
    c.store.set_setting("gtp", g, c.user)
    return g


@route("GET", "/api/consent")
def r_consent(c: Ctx) -> Any:
    aid = c.aid()
    return {"consents": c.store.consents(aid), "categories": config.features()["consent_categories"]}


@route("POST", "/api/consent")
def r_set_consent(c: Ctx) -> Any:
    """Grant / withdraw consent (only the astronaut themself)."""
    aid = c.aid()
    if c.claims.get("aid") != aid:  # type: ignore[union-attr]
        raise ApiError(403, "only the astronaut can change their own consent")
    c.store.set_consent(aid, str(c.b("category")), bool(c.b("granted")), c.user)
    return {"consents": c.store.consents(aid)}


@route("POST", "/api/flags", "thresholds_edit")
def r_flags(c: Ctx) -> Any:
    """Enable/disable a feature (flight surgeon)."""
    c.store.set_setting(f"flag.{c.b('feature')}", bool(c.b("enabled")), c.user)
    return {f: is_enabled(c.store, f) for f in config.features()["flags"]}


@route("POST", "/api/thresholds", "thresholds_edit")
def r_thresholds(c: Ctx) -> Any:
    """Edit one threshold rule (flight surgeon); written to config/thresholds.json."""
    th = json.loads(json.dumps(config.thresholds()))
    ind = th["indicators"][str(c.b("indicator"))]
    for k in ("red_if", "yellow_if"):
        if c.b(k) is not None:
            ind[k] = c.b(k)
    ind["review_needed"] = False
    ind["reviewed_by"] = c.user
    ind["reviewed_at"] = fhir.now_iso()
    (config.CONFIG_DIR / "thresholds.json").write_text(json.dumps(th, indent=2, ensure_ascii=False), encoding="utf-8")
    config.load.cache_clear()
    c.store.bb_append(c.user, "thresholds.edit", {"indicator": c.b("indicator"), "red_if": ind["red_if"], "yellow_if": ind["yellow_if"]})
    return ind


@route("GET", "/api/scenarios")
def r_scen(c: Ctx) -> Any:
    return synthetic.SCENARIOS


@route("POST", "/api/scenario")
def r_run_scen(c: Ctx) -> Any:
    """Load a SYNTHETIC scenario for one astronaut (CMO / flight surgeon)."""
    if c.role not in ("cmo", "flight_surgeon"):
        raise ApiError(403, "CMO or flight surgeon only")
    return synthetic.generate(c.store, str(c.b("aid")), str(c.b("scenario")), int(c.b("days", 10)))


@route("POST", "/api/import/fhir")
def r_import_fhir(c: Ctx) -> Any:
    """Import a FHIR Bundle produced by the REAL-data loader."""
    if c.role not in ("cmo", "flight_surgeon"):
        raise ApiError(403, "CMO or flight surgeon only")
    b = c.b("bundle") or {}
    n = 0
    for e in b.get("entry", []):
        r = e["resource"]
        if r.get("resourceType") != "Observation":
            continue
        aid = r["subject"]["reference"].split("/", 1)[1]
        c.store.add_astronaut(aid, aid, aid)
        c.store.add_observation(r, c.user)
        n += 1
    return {"imported": n}


# -------- F4 Smart Doctor
@route("GET", "/api/cdss/protocols")
def r_cdss_list(c: Ctx) -> Any:
    return {"protocols": cdss.list_protocols(), "lint": cdss.lint_protocols()}


@route("POST", "/api/cdss/start")
def r_cdss_start(c: Ctx) -> Any:
    return cdss.start(c.store, str(c.b("protocol")), c.aid(write=True), c.user)


@route("POST", "/api/cdss/answer")
def r_cdss_answer(c: Ctx) -> Any:
    return cdss.answer(c.store, str(c.b("session")), str(c.b("answer")), c.user)


# -------- F11 NASA-grounded AI assistant (EXPERIMENTAL, online, opt-in)
@route("GET", "/api/assistant/status")
def r_ai_status(c: Ctx) -> Any:
    """Is the AI assistant set up? Never returns the key itself."""
    return {**assistant.status(c.store), "enabled": is_enabled(c.store, "F11_assistant")}


@route("POST", "/api/assistant/key", "thresholds_edit")
def r_ai_key(c: Ctx) -> Any:
    """Set or remove the OpenRouter API key (stored encrypted) and optionally the model id."""
    try:
        assistant.set_key(c.store, c.b("key") or None, c.user)
    except assistant.AssistantError as e:
        raise ApiError(400, str(e)) from e
    m = str(c.b("model") or "").strip()
    if m:
        if not re.fullmatch(r"[A-Za-z0-9_./:\-]{3,100}", m):
            raise ApiError(400, "invalid model id")
        c.store.set_setting(assistant.MODEL_SETTING, m, c.user)
    return assistant.status(c.store)


@route("POST", "/api/assistant/ask")
def r_ai_ask(c: Ctx) -> Any:
    """Ask the NASA-grounded assistant. Sends only the question and NASA/CSA excerpts to OpenRouter."""
    if not is_enabled(c.store, "F11_assistant"):
        raise ConsentError("F11_assistant is disabled")
    if c.role == "astronaut":
        require(c.store, "F11_assistant", c.aid())
    try:
        return assistant.ask(c.store, str(c.b("question") or ""), "ar" if c.b("lang") == "ar" else "en")
    except assistant.AssistantError as e:
        raise ApiError(400, str(e)) from e


# -------- F5 Radiation
@route("GET", "/api/radiation")
def r_rad(c: Ctx) -> Any:
    return {**radiation.summary(c.store, c.aid()), "spe": c.store.get_setting("spe"),
            "crew": [radiation.summary(c.store, a["id"]) | {"readings": []} for a in c.store.astronauts()]
            if auth.can(c.role, "crew_vitals") else []}


@route("POST", "/api/radiation/reading")
def r_rad_add(c: Ctx) -> Any:
    return radiation.add_reading(c.store, c.aid(write=True), float(c.b("dose_msv")), c.b("ts"), c.user)


@route("POST", "/api/radiation/import")
def r_rad_imp(c: Ctx) -> Any:
    if c.role not in ("cmo", "flight_surgeon"):
        raise ApiError(403, "CMO or flight surgeon only")
    return radiation.import_csv(c.store, str(c.b("text", "")), c.user)


@route("GET", "/api/radiation/heatmap")
def r_heat(c: Ctx) -> Any:
    return radiation.heatmap(c.store, c.arg("spe") == "1")


@route("POST", "/api/radiation/zones")
def r_zones(c: Ctx) -> Any:
    if c.role not in ("cmo", "flight_surgeon"):
        raise ApiError(403, "CMO or flight surgeon only")
    radiation.save_zones(c.store, list(c.b("zones")), c.user)
    return radiation.heatmap(c.store)


@route("POST", "/api/radiation/spe")
def r_spe(c: Ctx) -> Any:
    """Start SPE mode (alarm, countdown, shelter, dose saved)."""
    if c.role in ("researcher", "bhs"):
        raise ApiError(403, "not allowed")
    return radiation.start_spe(c.store, float(c.b("arrival_min", 30)), float(c.b("duration_h", 8)),
                               str(c.b("zone", "z1")), c.user)


@route("POST", "/api/radiation/spe/stop")
def r_spe_stop(c: Ctx) -> Any:
    radiation.stop_spe(c.store, c.user)
    return {"ok": True}


# -------- F2 Vision
@route("GET", "/api/vision/chart")
def r_chart(c: Ctx) -> Any:
    return {"rows": vision.chart(float(c.arg("distance", "40") or 40), float(c.arg("pxmm", "3.78") or 3.78))}


@route("GET", "/api/vision")
def r_vision(c: Ctx) -> Any:
    aid = c.aid()
    imgs = [{k: v for k, v in r["payload"].items() if k != "b64"} | {"id": r["id"], "ts": r["ts"]}
            for r in c.store.records("vision", "image", aid)]
    return {"screenings": c.store.records("vision", "screening", aid), "images": imgs,
            "blink": c.store.records("vision", "blink", aid)[-10:]}


@route("GET", "/api/vision/image/{id}")
def r_vision_img(c: Ctx) -> Any:
    aid = c.aid()
    r = next((x for x in c.store.records("vision", "image", aid) if x["id"] == c.params["id"]), None)
    if not r:
        raise ApiError(404, "image not found")
    return (r["payload"]["mime"], base64.b64decode(r["payload"]["b64"]))


@route("POST", "/api/vision/screening")
def r_vis_scr(c: Ctx) -> Any:
    return vision.save_screening(c.store, c.aid(write=True), dict(c.b("result")), c.user)


@route("POST", "/api/vision/image")
def r_vis_img(c: Ctx) -> Any:
    return vision.save_image(c.store, c.aid(write=True), str(c.b("filename")), base64.b64decode(str(c.b("b64"))),
                             str(c.b("eye", "OD")), str(c.b("modality", "fundus")), bool(c.b("is_baseline")), c.user)


@route("POST", "/api/vision/blink")
def r_blink(c: Ctx) -> Any:
    return vision.save_blink(c.store, c.aid(write=True), float(c.b("blinks_per_min")), float(c.b("closure_ratio", 0)), c.user)


# -------- F6 Urine
@route("GET", "/api/urine")
def r_urine(c: Ctx) -> Any:
    return urine.analyse(c.store, c.aid())


@route("GET", "/api/urine/schema", None)
def r_urine_schema(c: Ctx) -> Any:
    return urine.URINALYSIS_SCHEMA


@route("POST", "/api/urine")
def r_urine_add(c: Ctx) -> Any:
    aid = c.aid(write=True)
    rec = dict(c.body or {})
    rec["astronaut_id"] = aid
    rec.pop("aid", None)
    rec.setdefault("timestamp", fhir.now_iso())
    rec.setdefault("source", "manual_strip")
    return urine.ingest(c.store, rec, c.user)


@route("POST", "/api/urine/import")
def r_urine_imp(c: Ctx) -> Any:
    if c.role not in ("cmo", "flight_surgeon"):
        raise ApiError(403, "CMO or flight surgeon only")
    return urine.import_file(c.store, str(c.b("text", "")), str(c.b("filename", "x.csv")), c.user)


# -------- F7 Coach
@route("GET", "/api/coach")
def r_coach(c: Ctx) -> Any:
    return coach.plan(c.store, c.aid())


@route("POST", "/api/coach/exercise")
def r_coach_ex(c: Ctx) -> Any:
    return coach.log_exercise(c.store, c.aid(write=True), str(c.b("device")), float(c.b("minutes")), c.user)


@route("GET", "/api/coach/board")
def r_board(c: Ctx) -> Any:
    return {"board": coach.crew_board(c.store)}


# -------- F1 Voice
@route("POST", "/api/voice")
def r_voice(c: Ctx) -> Any:
    """Submit prosodic FEATURES only (raw audio rejected)."""
    aid = c.aid(write=True)
    if c.claims.get("aid") != aid:  # type: ignore[union-attr]
        raise ApiError(403, "voice check-in is self-only")
    return voice.submit(c.store, aid, dict(c.b("features")), c.user)


@route("GET", "/api/voice")
def r_voice_get(c: Ctx) -> Any:
    aid = c.aid(behavioral=True)
    return {"checkins": c.store.records("voice", "checkin", aid)[-14:]}


# -------- F3 Crew
@route("POST", "/api/crew/interaction")
def r_inter(c: Ctx) -> Any:
    aid = c.aid(write=True)
    return crew.log_interaction(c.store, aid, dict(c.body or {}), c.user)


@route("POST", "/api/crew/survey")
def r_survey(c: Ctx) -> Any:
    aid = c.aid(write=True)
    return crew.survey(c.store, aid, int(c.b("cohesion")), int(c.b("conflict")), int(c.b("workload")), c.user)


@route("GET", "/api/crew/index")
def r_team(c: Ctx) -> Any:
    """Team-level index (no individual data)."""
    return crew.team_index(c.store)


@route("GET", "/api/crew/isolation")
def r_iso(c: Ctx) -> Any:
    """Isolation signal: visible ONLY to the individual and the BHS."""
    aid = str(c.b("aid") or c.arg("aid") or (c.claims or {}).get("aid"))
    if not (c.role == "bhs" or (c.claims or {}).get("aid") == aid):
        raise ApiError(403, "isolation signal is visible only to the individual and the behavioral health specialist")
    return crew.isolation_signal(c.store, aid)


# -------- F8 Connection
@route("GET", "/api/connection")
def r_conn(c: Ctx) -> Any:
    aid = c.aid(behavioral=True)
    return {"suggest": connection.should_suggest(c.store, aid), "library": connection.library(aid),
            "off": bool(c.store.get_setting(f"nostalgia_off.{aid}"))}


@route("POST", "/api/connection/rate")
def r_conn_rate(c: Ctx) -> Any:
    return connection.rate(c.store, c.aid(write=True), bool(c.b("helped")), c.user)


@route("POST", "/api/connection/off")
def r_conn_off(c: Ctx) -> Any:
    aid = c.aid(write=True)
    c.store.set_setting(f"nostalgia_off.{aid}", bool(c.b("off")), c.user)
    return {"off": bool(c.b("off"))}


# -------- F9 Black box
@route("GET", "/api/blackbox")
def r_bb(c: Ctx) -> Any:
    if c.role not in ("cmo", "flight_surgeon"):
        raise ApiError(403, "CMO or flight surgeon only")
    ents = c.store.bb_entries(int(c.arg("limit", "50") or 50))
    for e in ents:  # keep the listing light
        e["payload"] = json.dumps(e["payload"], ensure_ascii=False)[:300]
    return {"entries": ents}


@route("GET", "/api/blackbox/verify")
def r_bb_verify(c: Ctx) -> Any:
    """Tamper check of the whole hash chain."""
    return blackbox.verify(c.store)


@route("POST", "/api/blackbox/tamper_demo")
def r_bb_tamper(c: Ctx) -> Any:
    """Copies the DB, tampers with ONE entry in the copy, verifies the copy."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "copy.sqlite"
        with c.store._lock:
            src = sqlite3.connect(str(c.store.path))
            dst = sqlite3.connect(str(p))
            src.backup(dst)
            src.close()
        dst.execute("DROP TRIGGER bb_no_update")
        row = dst.execute("SELECT seq FROM blackbox ORDER BY seq LIMIT 1 OFFSET 3").fetchone()
        dst.execute("UPDATE blackbox SET actor='attacker' WHERE seq=?", (row[0],))
        dst.commit()
        dst.close()
        copy = Store(p, key=c.store.cipher._key)
        res = copy.bb_verify()
        copy.close()
    return {"original": c.store.bb_verify(), "tampered_copy": res, "tampered_seq": row[0]}


@route("GET", "/api/export", "research_export")
def r_export(c: Ctx) -> Any:
    """Pseudonymised research export (OAIS SIP zip)."""
    data, _ = blackbox.research_export(c.store, c.app.pseudo_secret, c.user)
    return ("application/zip", data)


# -------- Science: evidence registry, simulation, history
@route("GET", "/api/evidence", None)
def r_evidence(c: Ctx) -> Any:
    """Scientific evidence registry (every value with its source)."""
    return {"entries": physio.evidence(), "verified_on": config.load("evidence").get("_verified_on")}


@route("GET", "/api/physio/atmosphere", None)
def r_atm(c: Ctx) -> Any:
    """Pressure/altitude oxygenation estimate (published equations, SIMULATED)."""
    preset = c.arg("cabin")
    if preset:
        cab = physio.CABINS[preset]
        kpa, fio2 = float(cab["kpa"]), float(cab["fio2"])
    elif c.arg("alt") is not None:
        kpa, fio2 = physio.pressure_at_altitude(float(c.arg("alt") or 0)) / 1000, float(c.arg("fio2", "0.2095") or 0.2095)
    else:
        kpa, fio2 = float(c.arg("kpa", "101.325") or 101.325), float(c.arg("fio2", "0.2095") or 0.2095)
    paco2 = float(c.arg("paco2", "40") or 40)
    return {"result": physio.oxygenation(kpa, fio2, paco2), "curve": physio.altitude_curve(fio2, paco2),
            "cabins": {k: {**v, "kpa": round(float(v["kpa"]), 2)} for k, v in physio.CABINS.items()},
            "co2": physio.co2_level(float(c.arg("co2", "3000") or 3000), kpa)}


@route("GET", "/api/physio/gravity")
def r_grav(c: Ctx) -> Any:
    """Evidence-bound gravity/time-in-flight expectations applied to the personal baseline (SIMULATED)."""
    aid = c.aid()
    base: dict[str, float] = {}
    for ind, k in (("systolic", "sys"), ("diastolic", "dia"), ("heart_rate", "hr")):
        b = engine.baseline(c.store.observations(aid, ind), "earth_preflight")
        if b:
            base[k] = float(b["mean"])
    phase, day = str(c.arg("phase", "flight")), float(c.arg("day", "30") or 30)
    mission = float(c.arg("mission", "180") or 180)
    return {"baseline": base, "effects": physio.gravity_effects(phase, day, mission, base, str(c.arg("gravity", "micro"))),
            "bone": physio.bone_projection(int(max(mission, day))), "phases": physio.phase_comparison(base)}


@route("POST", "/api/cabin")
def r_cabin(c: Ctx) -> Any:
    """Select the cabin atmosphere used for CO2 partial-pressure evaluation."""
    preset = str(c.b("preset"))
    if preset not in physio.CABINS:
        raise ApiError(400, "unknown cabin preset")
    c.store.set_setting("cabin_preset", preset, c.user)
    return {"cabin_preset": preset}


@route("GET", "/api/history")
def r_history(c: Ctx) -> Any:
    """Measurement history (all stored observations for one astronaut, newest first)."""
    aid = c.aid()
    ind = c.arg("indicator")
    rows = []
    for o in reversed(c.store.observations(aid, ind)):
        rows.append({"t": o["effectiveDateTime"], "indicator": fhir.indicator_of(o), "value": fhir.value_of(o),
                     "unit": o["valueQuantity"]["unit"], "prov": fhir.provenance_of(o), "ctx": fhir.gravity_of(o),
                     "conf": fhir.conditions_of(o).get("confidence", "")})
    return {"rows": rows[: int(c.arg("limit", "300") or 300)], "total": len(rows)}


# -------- Posture verification (OpenCV + MediaPipe)
@route("GET", "/api/pose/status", None)
def r_pose_status(c: Ctx) -> Any:
    """Which vision tier is available (full / opencv_only / manual)."""
    return pose.capabilities()


@route("GET", "/api/pose/exams", None)
def r_pose_exams(c: Ctx) -> Any:
    return {"exams": pose.exams()}


@route("POST", "/api/pose/start")
def r_pose_start(c: Ctx) -> Any:
    """Start a guided posture session. Camera mode requires consent 'pose_camera'."""
    aid = c.aid(write=True)
    mode = str(c.b("mode", "camera"))
    if mode == "camera":
        from .consent import require
        require(c.store, "F10_pose", aid)
    v = pose.start(str(c.b("exam")), str(c.b("side", "left")), mode)
    pose.get(v["session"])["aid"] = aid
    return v


@route("POST", "/api/pose/frame")
def r_pose_frame(c: Ctx) -> Any:
    """Analyse ONE camera frame (processed in memory, never stored)."""
    return pose.frame(str(c.b("session")), str(c.b("image")))


@route("POST", "/api/pose/manual")
def r_pose_manual(c: Ctx) -> Any:
    return pose.manual(str(c.b("session")), bool(c.b("confirmed", True)))


@route("POST", "/api/pose/finish")
def r_pose_finish(c: Ctx) -> Any:
    """Finish: only the step summary and compliance score are stored."""
    s = pose.get(str(c.b("session")))
    aid = s.get("aid") or c.aid()
    out = pose.finish(str(c.b("session")))
    c.store.add_record("pose", "session", out, aid, c.user)
    return out


@route("GET", "/api/pose/sessions")
def r_pose_sessions(c: Ctx) -> Any:
    return {"sessions": c.store.records("pose", "session", c.aid())[-20:]}


@route("GET", "/api/openapi.json", None)
def r_openapi(c: Ctx) -> Any:
    """OpenAPI 3.0 description generated from the route table."""
    paths: dict[str, Any] = {}
    for m, pat, fn, perm, doc in ROUTES:
        p = pat.pattern.strip("^$").replace("(?P<", "{").replace(">[^/]+)", "}")
        paths.setdefault(p, {})[m.lower()] = {"summary": doc or fn.__name__, "security": [] if perm is None else [{"bearer": []}],
                                              "x-permission": perm, "responses": {"200": {"description": "OK"}}}
    return {"openapi": "3.0.3", "info": {"title": "BÖVD API", "version": VERSION,
                                         "description": "Hackathon prototype – decision support only, not a medical device."},
            "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}},
            "paths": paths}


# =============================================================== HTTP glue
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".webmanifest": "application/manifest+json",
        ".jpg": "image/jpeg", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".mp4": "video/mp4", ".ogg": "audio/ogg", ".webm": "video/webm"}


def make_handler(app: App) -> type[BaseHTTPRequestHandler]:
    class H(BaseHTTPRequestHandler):
        server_version = "BÖVD"

        def log_message(self, fmt: str, *args: Any) -> None:  # quieter console
            if "/api/poll" not in (args[0] if args else ""):
                sys.stderr.write("[http] " + fmt % args + "\n")

        def _send(self, status: int, ctype: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(body)

        def _api(self, method: str) -> None:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 30 * 1024 * 1024:
                return self._send(413, "application/json", b'{"error":"too large"}')
            body = self.rfile.read(n) if n else b""
            st, ct, out = app.dispatch(method, self.path, {k.lower(): v for k, v in self.headers.items()}, body)
            self._send(st, ct, out)

        def do_POST(self) -> None:  # noqa: N802
            self._api("POST")

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path.startswith("/api/"):
                return self._api("GET")
            if path.startswith("/media/"):
                return self._media(path)
            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            f = (WEB_DIR / rel).resolve()
            if WEB_DIR.resolve() not in f.parents or not f.is_file():
                return self._send(404, "text/plain", b"not found")
            self._send(200, MIME.get(f.suffix, "application/octet-stream"), f.read_bytes())

        def _media(self, path: str) -> None:
            q = parse_qs(urlparse(self.path).query)
            claims = auth.read_token(app.secret, (q.get("token") or [""])[0])
            parts = path.split("/")
            if len(parts) != 4 or not claims or claims.get("aid") != parts[2]:
                return self._send(403, "text/plain", b"owner only")
            f = (DATA_DIR / "media" / parts[2] / parts[3]).resolve()
            if (DATA_DIR / "media").resolve() not in f.parents or not f.is_file():
                return self._send(404, "text/plain", b"not found")
            self._send(200, MIME.get(f.suffix.lower(), "application/octet-stream"), f.read_bytes())

    return H


def _ticker(app: App) -> None:
    while True:
        try:
            alerts.tick(app.store)
        except Exception:  # pragma: no cover
            traceback.print_exc()
        time.sleep(5)


def main() -> None:  # pragma: no cover
    port = int(os.environ.get("ASTRA_PORT", "8765"))
    print("=" * 66)
    print(" BÖVD – hackathon prototype (decision support / training)")
    print(" NOT a certified medical device. Thresholds need flight-surgeon review.")
    print(f" Crypto backend: {crypto.BACKEND}")
    print("=" * 66)
    app = App()
    threading.Thread(target=_ticker, args=(app,), daemon=True).start()
    bind = os.environ.get("ASTRA_BIND", "127.0.0.1")  # loopback only; Docker sets 0.0.0.0 inside the container
    srv = ThreadingHTTPServer((bind, port), make_handler(app))
    url = f"http://127.0.0.1:{port}/"
    print(f"[BÖVD] Running at {url}  (Ctrl+C to stop)")
    print(f"[BÖVD] Demo users: astro1 / cmo1 / bhs1 / surgeon1 / research1  · password: {DEMO_PASSWORD}")
    if os.environ.get("ASTRA_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[BÖVD] stopped.")


if __name__ == "__main__":  # pragma: no cover
    main()

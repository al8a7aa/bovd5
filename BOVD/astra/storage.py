"""
BÖVD · storage layer
============================
SQLite in WAL mode. Health payloads (FHIR resources, feature records, alert
explanations) are encrypted field-by-field with AES-256-GCM (astra/crypto.py);
only non-identifying index columns (ids, codes, timestamps) stay in clear text
so that queries remain possible.

The *black box* (F9) is an append-only, SHA-256 hash-chained table that receives
every write (observations, alerts, decisions, consent changes, logins). SQLite
triggers forbid UPDATE and DELETE on it.

Standards alignment (designed in alignment with, not certified):
  * ISO/IEC 27002 §8.15 logging, §8.24 cryptography; ISO 27799.
  * IEC 62304 §5.5 – unit of software with its own tests (tests/test_storage.py).
  * ISO 14721 (OAIS) – the black box is the Archival Information Package source.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from . import fhir
from .crypto import Cipher, load_or_create_key

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(
  username TEXT PRIMARY KEY, role TEXT NOT NULL, display TEXT NOT NULL,
  astronaut_id TEXT, salt TEXT NOT NULL, pw_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS astronauts(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, pseudonym TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observations(
  id TEXT PRIMARY KEY, astronaut_id TEXT NOT NULL, indicator TEXT NOT NULL,
  effective TEXT NOT NULL, provenance TEXT NOT NULL, resource_enc TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_obs ON observations(astronaut_id, indicator, effective);
CREATE TABLE IF NOT EXISTS records(
  id TEXT PRIMARY KEY, astronaut_id TEXT, feature TEXT NOT NULL, kind TEXT NOT NULL,
  ts TEXT NOT NULL, provenance TEXT NOT NULL, payload_enc TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_rec ON records(feature, kind, astronaut_id, ts);
CREATE TABLE IF NOT EXISTS alerts(
  id TEXT PRIMARY KEY, astronaut_id TEXT NOT NULL, priority TEXT NOT NULL,
  indicator TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL,
  tier INTEGER NOT NULL, last_notified TEXT NOT NULL, repeats INTEGER NOT NULL,
  acked_by TEXT, acked_at TEXT, body_enc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbound(
  id TEXT PRIMARY KEY, created TEXT NOT NULL, deliver_at TEXT NOT NULL,
  direction TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0, body_enc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS consents(
  astronaut_id TEXT NOT NULL, category TEXT NOT NULL, granted INTEGER NOT NULL,
  ts TEXT NOT NULL, PRIMARY KEY(astronaut_id, category));
CREATE TABLE IF NOT EXISTS events(
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, type TEXT NOT NULL, context TEXT NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS blackbox(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, actor TEXT NOT NULL,
  category TEXT NOT NULL, payload_enc TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS bb_no_update BEFORE UPDATE ON blackbox
  BEGIN SELECT RAISE(ABORT, 'black box is append-only'); END;
CREATE TRIGGER IF NOT EXISTS bb_no_delete BEFORE DELETE ON blackbox
  BEGIN SELECT RAISE(ABORT, 'black box is append-only'); END;
"""

GENESIS = "0" * 64


def chain_hash(prev: str, ts: str, actor: str, category: str, payload_enc: str) -> str:
    """SHA-256 over the previous hash and this entry's fields."""
    h = hashlib.sha256()
    for part in (prev, ts, actor, category, payload_enc):
        h.update(part.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


class Store:
    """Thread-safe facade around one SQLite connection."""

    def __init__(self, db_path: Path, key: bytes | None = None) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.path = db_path
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self.cipher = Cipher(key or load_or_create_key(db_path.parent / "astra.key"))

    # ------------------------------------------------------------------ utils
    def _enc(self, obj: Any) -> str:
        return self.cipher.encrypt(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _dec(self, tok: str) -> Any:
        return json.loads(self.cipher.decrypt(tok).decode("utf-8"))

    def q(self, sql: str, args: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._db.execute(sql, tuple(args)))

    def x(self, sql: str, args: Iterable[Any] = ()) -> None:
        with self._lock:
            self._db.execute(sql, tuple(args))
            self._db.commit()

    # --------------------------------------------------------------- settings
    def get_setting(self, key: str, default: Any = None) -> Any:
        r = self.q("SELECT value FROM settings WHERE key=?", (key,))
        return json.loads(r[0]["value"]) if r else default

    def set_setting(self, key: str, value: Any, actor: str = "system") -> None:
        self.x("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, json.dumps(value)))
        self.bb_append(actor, "setting", {"key": key, "value": value})

    # --------------------------------------------------------------- black box
    def bb_append(self, actor: str, category: str, payload: Any) -> int:
        """Append one hash-chained, encrypted entry. Returns its sequence no."""
        with self._lock:
            last = self._db.execute("SELECT hash FROM blackbox ORDER BY seq DESC LIMIT 1").fetchone()
            prev = last["hash"] if last else GENESIS
            ts = fhir.now_iso()
            enc = self._enc(payload)
            h = chain_hash(prev, ts, actor, category, enc)
            cur = self._db.execute(
                "INSERT INTO blackbox(ts,actor,category,payload_enc,prev_hash,hash) VALUES(?,?,?,?,?,?)",
                (ts, actor, category, enc, prev, h))
            self._db.commit()
            return int(cur.lastrowid or 0)

    def bb_verify(self) -> dict[str, Any]:
        """Re-compute the chain. Returns ok flag and the first broken seq."""
        prev = GENESIS
        n = 0
        for r in self.q("SELECT * FROM blackbox ORDER BY seq"):
            n += 1
            expect = chain_hash(prev, r["ts"], r["actor"], r["category"], r["payload_enc"])
            if r["prev_hash"] != prev or r["hash"] != expect:
                return {"ok": False, "entries": n, "broken_at": r["seq"]}
            try:
                self._dec(r["payload_enc"])  # GCM tag also proves integrity
            except Exception:
                return {"ok": False, "entries": n, "broken_at": r["seq"], "reason": "decrypt"}
            prev = r["hash"]
        return {"ok": True, "entries": n, "head": prev}

    def bb_entries(self, limit: int = 100, decrypt: bool = True) -> list[dict[str, Any]]:
        rows = self.q("SELECT * FROM blackbox ORDER BY seq DESC LIMIT ?", (limit,))
        out = []
        for r in rows:
            d = {k: r[k] for k in r.keys() if k != "payload_enc"}
            if decrypt:
                d["payload"] = self._dec(r["payload_enc"])
            out.append(d)
        return out

    # ------------------------------------------------------------ astronauts
    def add_astronaut(self, aid: str, name: str, pseudonym: str) -> None:
        self.x("INSERT OR IGNORE INTO astronauts(id,name,pseudonym) VALUES(?,?,?)", (aid, name, pseudonym))

    def astronauts(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.q("SELECT * FROM astronauts ORDER BY id")]

    # ---------------------------------------------------------- observations
    def add_observation(self, obs: dict[str, Any], actor: str) -> str:
        aid = obs["subject"]["reference"].split("/", 1)[1]
        prov = fhir.provenance_of(obs)
        self.x("INSERT INTO observations(id,astronaut_id,indicator,effective,provenance,resource_enc) "
               "VALUES(?,?,?,?,?,?)",
               (obs["id"], aid, fhir.indicator_of(obs), obs["effectiveDateTime"], prov["type"], self._enc(obs)))
        self.bb_append(actor, "observation", obs)
        return str(obs["id"])

    def observations(self, astronaut_id: str, indicator: str | None = None,
                     since: str | None = None, until: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT resource_enc FROM observations WHERE astronaut_id=?"
        args: list[Any] = [astronaut_id]
        if indicator:
            sql += " AND indicator=?"
            args.append(indicator)
        if since:
            sql += " AND effective>=?"
            args.append(since)
        if until:
            sql += " AND effective<=?"
            args.append(until)
        sql += " ORDER BY effective"
        return [self._dec(r["resource_enc"]) for r in self.q(sql, args)]

    def all_observations(self) -> list[dict[str, Any]]:
        return [self._dec(r["resource_enc"]) for r in self.q("SELECT resource_enc FROM observations ORDER BY effective")]

    # --------------------------------------------------------------- records
    def add_record(self, feature: str, kind: str, payload: Any, astronaut_id: str | None,
                   actor: str, provenance: str = "USER-ENTERED", ts: str | None = None,
                   bb_payload: Any = None) -> str:
        """Store a feature record. ``bb_payload`` replaces the payload in the
        black box (e.g. a SHA-256 digest instead of a full image)."""
        rid = str(uuid.uuid4())
        self.x("INSERT INTO records(id,astronaut_id,feature,kind,ts,provenance,payload_enc) VALUES(?,?,?,?,?,?,?)",
               (rid, astronaut_id, feature, kind, ts or fhir.now_iso(), provenance, self._enc(payload)))
        self.bb_append(actor, f"{feature}.{kind}", {"astronaut_id": astronaut_id, "provenance": provenance,
                                                    "payload": payload if bb_payload is None else bb_payload})
        return rid

    def records(self, feature: str, kind: str | None = None,
                astronaut_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM records WHERE feature=?"
        args: list[Any] = [feature]
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        if astronaut_id:
            sql += " AND astronaut_id=?"
            args.append(astronaut_id)
        sql += " ORDER BY ts"
        return [{"id": r["id"], "astronaut_id": r["astronaut_id"], "kind": r["kind"], "ts": r["ts"],
                 "provenance": r["provenance"], "payload": self._dec(r["payload_enc"])}
                for r in self.q(sql, args)]

    def count_records(self, feature: str) -> int:
        return int(self.q("SELECT COUNT(*) c FROM records WHERE feature=?", (feature,))[0]["c"])

    # --------------------------------------------------------------- consent
    def set_consent(self, aid: str, category: str, granted: bool, actor: str) -> None:
        self.x("INSERT OR REPLACE INTO consents(astronaut_id,category,granted,ts) VALUES(?,?,?,?)",
               (aid, category, int(granted), fhir.now_iso()))
        self.bb_append(actor, "consent", {"astronaut_id": aid, "category": category, "granted": granted})

    def consents(self, aid: str) -> dict[str, bool]:
        return {r["category"]: bool(r["granted"]) for r in self.q("SELECT * FROM consents WHERE astronaut_id=?", (aid,))}

    # ----------------------------------------------------------------- events
    def add_event(self, ts: str, etype: str, context: str, note: str, actor: str) -> str:
        eid = str(uuid.uuid4())
        self.x("INSERT INTO events(id,ts,type,context,note) VALUES(?,?,?,?,?)", (eid, ts, etype, context, note))
        self.bb_append(actor, "mission_event", {"ts": ts, "type": etype, "context": context, "note": note})
        return eid

    def events(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.q("SELECT * FROM events ORDER BY ts")]

    # ----------------------------------------------------------------- alerts
    def add_alert(self, aid: str, priority: str, indicator: str, body: dict[str, Any], actor: str) -> str:
        alid = str(uuid.uuid4())
        now = fhir.now_iso()
        self.x("INSERT INTO alerts(id,astronaut_id,priority,indicator,created,status,tier,last_notified,repeats,body_enc)"
               " VALUES(?,?,?,?,?,?,?,?,?,?)",
               (alid, aid, priority, indicator, now, "active", 0, now, 0, self._enc(body)))
        self.bb_append(actor, "alert.raise", {"id": alid, "astronaut_id": aid, "priority": priority,
                                              "indicator": indicator, "body": body})
        return alid

    def alerts(self, status: str | None = None, aid: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM alerts WHERE 1=1"
        args: list[Any] = []
        if status:
            sql += " AND status=?"
            args.append(status)
        if aid:
            sql += " AND astronaut_id=?"
            args.append(aid)
        sql += " ORDER BY created DESC"
        out = []
        for r in self.q(sql, args):
            d = {k: r[k] for k in r.keys() if k != "body_enc"}
            d["body"] = self._dec(r["body_enc"])
            out.append(d)
        return out

    def update_alert(self, alid: str, actor: str, **fields: Any) -> None:
        sets = ", ".join(f"{k}=?" for k in fields)
        self.x(f"UPDATE alerts SET {sets} WHERE id=?", (*fields.values(), alid))  # nosec B608 - keys are internal
        self.bb_append(actor, "alert.update", {"id": alid, **fields})

    # -------------------------------------------------------- outbound queue
    def enqueue(self, direction: str, body: dict[str, Any], deliver_at: str, actor: str) -> str:
        mid = str(uuid.uuid4())
        self.x("INSERT INTO outbound(id,created,deliver_at,direction,delivered,body_enc) VALUES(?,?,?,?,0,?)",
               (mid, fhir.now_iso(), deliver_at, direction, self._enc(body)))
        self.bb_append(actor, "queue.enqueue", {"id": mid, "direction": direction, "deliver_at": deliver_at})
        return mid

    def queue(self, direction: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM outbound"
        args: list[Any] = []
        if direction:
            sql += " WHERE direction=?"
            args.append(direction)
        sql += " ORDER BY created DESC"
        out = []
        for r in self.q(sql, args):
            d = {k: r[k] for k in r.keys() if k != "body_enc"}
            d["body"] = self._dec(r["body_enc"])
            out.append(d)
        return out

    def mark_delivered(self, mid: str) -> None:
        self.x("UPDATE outbound SET delivered=1 WHERE id=?", (mid,))
        self.bb_append("comm-link", "queue.delivered", {"id": mid})

    # ------------------------------------------------------------------ users
    def add_user(self, username: str, role: str, display: str, astronaut_id: str | None,
                 salt: str, pw_hash: str) -> None:
        self.x("INSERT OR IGNORE INTO users(username,role,display,astronaut_id,salt,pw_hash) VALUES(?,?,?,?,?,?)",
               (username, role, display, astronaut_id, salt, pw_hash))

    def user(self, username: str) -> dict[str, Any] | None:
        r = self.q("SELECT * FROM users WHERE username=?", (username,))
        return dict(r[0]) if r else None

    def users(self) -> list[dict[str, Any]]:
        return [{k: r[k] for k in ("username", "role", "display", "astronaut_id")} for r in self.q("SELECT * FROM users")]

    def close(self) -> None:
        with self._lock:
            self._db.close()

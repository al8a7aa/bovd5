"""
BÖVD · authentication and role-based access
===================================================
* Passwords: PBKDF2-HMAC-SHA256, 200 000 iterations, 16-byte random salt.
* Tokens: JWT (RFC 7519) HS256, 12-hour expiry, implemented with the standard
  library (hmac + base64) so the app runs without extra packages.
* Roles: astronaut, cmo (crew medical officer), bhs (behavioral health
  specialist), flight_surgeon, researcher.

Access matrix (least privilege, ISO/IEC 27002 §5.15, §8.2):

  ====================  =====  ====  ===  ==============  ==========
  permission            astro  cmo   bhs  flight_surgeon  researcher
  ====================  =====  ====  ===  ==============  ==========
  own data read/write    ✔     ✔     ✔        ✔               –
  all crew vitals        –     ✔     –        ✔               –
  behavioural/isolation  own   –     ✔        –               –
  thresholds edit        –     –     –        ✔               –
  research export        –     –     –        ✔               ✔ (pseudonymised)
  ====================  =====  ====  ===  ==============  ==========
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

ROLES = ("astronaut", "cmo", "bhs", "flight_surgeon", "researcher")
PERMS: dict[str, set[str]] = {
    "astronaut": {"self_read", "self_write", "self_behavior", "ack_own"},
    "cmo": {"self_read", "self_write", "crew_vitals", "ack_any", "cdss"},
    "bhs": {"behavior_all", "isolation_all"},
    "flight_surgeon": {"crew_vitals", "ack_any", "thresholds_edit", "research_export", "cdss", "ground"},
    "researcher": {"research_export"},
}


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _ub64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(pw: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 200_000)
    return salt.hex(), h.hex()


def verify_password(pw: str, salt_hex: str, hash_hex: str) -> bool:
    _, h = hash_password(pw, bytes.fromhex(salt_hex))
    return hmac.compare_digest(h, hash_hex)


def make_token(secret: bytes, user: dict[str, Any], ttl_s: int = 12 * 3600) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({"sub": user["username"], "role": user["role"],
                               "aid": user.get("astronaut_id"), "exp": int(time.time()) + ttl_s}).encode())
    sig = _b64(hmac.new(secret, f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def read_token(secret: bytes, token: str) -> dict[str, Any] | None:
    """Return the claims if the signature and expiry are valid, else None."""
    try:
        h, p, s = token.split(".")
        exp_sig = _b64(hmac.new(secret, f"{h}.{p}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(s, exp_sig):
            return None
        claims: dict[str, Any] = json.loads(_ub64(p))
        if claims["exp"] < time.time():
            return None
        return claims
    except Exception:
        return None


def can(role: str, perm: str) -> bool:
    return perm in PERMS.get(role, set())


def can_read_astronaut(claims: dict[str, Any], aid: str, behavioral: bool = False) -> bool:
    """Object-level access check for one astronaut's data."""
    if claims.get("aid") == aid and claims["role"] in ("astronaut", "cmo"):
        return True
    if behavioral:
        return can(claims["role"], "behavior_all")
    return can(claims["role"], "crew_vitals")

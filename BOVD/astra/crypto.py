"""
BÖVD · crypto (AES-256-GCM, at-rest encryption)
=======================================================
All health payloads are encrypted with AES-256-GCM before they reach SQLite.

* If the ``cryptography`` package is installed (``start.bat`` tries to install
  it), its audited OpenSSL implementation is used.
* Otherwise a pure-Python AES-256-GCM (NIST SP 800-38D) fallback is used so the
  prototype still runs fully offline with only the Python standard library.
  The fallback is verified bit-for-bit against ``cryptography`` in
  tests/test_crypto.py. It is slow and NOT side-channel hardened – acceptable
  for a hackathon prototype, not for flight software.

Key management (prototype): a random 256-bit key is generated on first run in
``data/db/astra.key`` (or taken from env ``ASTRA_KEY`` as 64 hex chars).
A real system would keep the key in a hardware security module.

Standards alignment (designed in alignment with, not certified):
  * ISO/IEC 27002:2022 §8.24 – use of cryptography.
  * ISO 27799 – protection of personal health information at rest.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

try:  # pragma: no cover - depends on the environment
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM

    BACKEND = "cryptography (OpenSSL)"
except Exception:  # pragma: no cover
    _AESGCM = None  # type: ignore[assignment,misc]
    BACKEND = "pure-python fallback"

# --------------------------------------------------------------------------- #
# Pure-Python AES-256 block cipher (FIPS-197)                                  #
# --------------------------------------------------------------------------- #
_SBOX = bytearray(256)


def _init_sbox() -> None:
    """Generate the AES S-box from the multiplicative inverse in GF(2^8)."""
    p = q = 1
    _SBOX[0] = 0x63
    while True:
        # multiply p by 3
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        # divide q by 3
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ (((q << 1) | (q >> 7)) & 0xFF) ^ (((q << 2) | (q >> 6)) & 0xFF) \
            ^ (((q << 3) | (q >> 5)) & 0xFF) ^ (((q << 4) | (q >> 4)) & 0xFF)
        _SBOX[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break


_init_sbox()


def _xtime(a: int) -> int:
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else a << 1


def _expand_key(key: bytes) -> list[list[int]]:
    """AES-256 key schedule → 15 round keys of 16 bytes."""
    nk, nr = 8, 14
    w = [list(key[4 * i: 4 * i + 4]) for i in range(nk)]
    rcon = 1
    for i in range(nk, 4 * (nr + 1)):
        t = list(w[i - 1])
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[b] for b in t]
            t[0] ^= rcon
            rcon = _xtime(rcon)
        elif i % nk == 4:
            t = [_SBOX[b] for b in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    return [sum(w[4 * r: 4 * r + 4], []) for r in range(nr + 1)]


# T-tables (combined SubBytes + ShiftRows + MixColumns) – ~4× faster in Python
_TE0 = [((_xtime(x) << 24) | (x << 16) | (x << 8) | (_xtime(x) ^ x)) for x in (_SBOX[i] for i in range(256))]
_TE1 = [((v >> 8) | (v << 24)) & 0xFFFFFFFF for v in _TE0]
_TE2 = [((v >> 16) | (v << 16)) & 0xFFFFFFFF for v in _TE0]
_TE3 = [((v >> 24) | (v << 8)) & 0xFFFFFFFF for v in _TE0]


def _words(rk: list[list[int]]) -> list[int]:
    return [int.from_bytes(bytes(r[4 * c:4 * c + 4]), "big") for r in rk for c in range(4)]


def _encrypt_block(rk: list[list[int]] | list[int], block: bytes) -> bytes:
    """Encrypt one 16-byte block. ``rk`` = round keys (bytes rows or words)."""
    w: list[int] = rk if isinstance(rk[0], int) else _words(rk)
    te0, te1, te2, te3 = _TE0, _TE1, _TE2, _TE3
    s0 = int.from_bytes(block[0:4], "big") ^ w[0]
    s1 = int.from_bytes(block[4:8], "big") ^ w[1]
    s2 = int.from_bytes(block[8:12], "big") ^ w[2]
    s3 = int.from_bytes(block[12:16], "big") ^ w[3]
    for r in range(1, 14):
        k = 4 * r
        n0 = te0[s0 >> 24] ^ te1[(s1 >> 16) & 255] ^ te2[(s2 >> 8) & 255] ^ te3[s3 & 255] ^ w[k]
        n1 = te0[s1 >> 24] ^ te1[(s2 >> 16) & 255] ^ te2[(s3 >> 8) & 255] ^ te3[s0 & 255] ^ w[k + 1]
        n2 = te0[s2 >> 24] ^ te1[(s3 >> 16) & 255] ^ te2[(s0 >> 8) & 255] ^ te3[s1 & 255] ^ w[k + 2]
        n3 = te0[s3 >> 24] ^ te1[(s0 >> 16) & 255] ^ te2[(s1 >> 8) & 255] ^ te3[s2 & 255] ^ w[k + 3]
        s0, s1, s2, s3 = n0, n1, n2, n3
    sb = _SBOX
    out = b""
    for a, b, c, d, kk in ((s0, s1, s2, s3, w[56]), (s1, s2, s3, s0, w[57]), (s2, s3, s0, s1, w[58]), (s3, s0, s1, s2, w[59])):
        out += (((sb[a >> 24] << 24) | (sb[(b >> 16) & 255] << 16) | (sb[(c >> 8) & 255] << 8) | sb[d & 255]) ^ kk).to_bytes(4, "big")
    return out


def _gmul(x: int, y: int) -> int:
    """Multiplication in GF(2^128) as defined for GHASH."""
    r = 0xE1 << 120
    z = 0
    for i in range(127, -1, -1):
        if (y >> i) & 1:
            z ^= x
        x = (x >> 1) ^ r if x & 1 else x >> 1
    return z


def _ghash(h: int, aad: bytes, ct: bytes) -> int:
    def blocks(b: bytes) -> list[bytes]:
        b = b + b"\x00" * ((16 - len(b) % 16) % 16)
        return [b[i:i + 16] for i in range(0, len(b), 16)]

    y = 0
    for blk in blocks(aad) + blocks(ct):
        y = _gmul(y ^ int.from_bytes(blk, "big"), h)
    lens = (len(aad) * 8).to_bytes(8, "big") + (len(ct) * 8).to_bytes(8, "big")
    return _gmul(y ^ int.from_bytes(lens, "big"), h)


_key_cache: dict[bytes, list[int]] = {}


def _gcm(key: bytes, nonce: bytes, data: bytes, aad: bytes, decrypt: bool,
         tag: bytes = b"") -> tuple[bytes, bytes]:
    rk = _key_cache.get(key)
    if rk is None:
        rk = _words(_expand_key(key))
        _key_cache[key] = rk
    h = int.from_bytes(_encrypt_block(rk, b"\x00" * 16), "big")
    j0 = nonce + b"\x00\x00\x00\x01"  # 96-bit nonce only
    ctr = int.from_bytes(j0, "big")
    out = bytearray()
    for i in range(0, len(data), 16):
        ctr = (ctr & ~0xFFFFFFFF) | ((ctr + 1) & 0xFFFFFFFF)
        ks = _encrypt_block(rk, ctr.to_bytes(16, "big"))
        chunk = data[i:i + 16]
        out += bytes(a ^ b for a, b in zip(chunk, ks, strict=False))
    ct = data if decrypt else bytes(out)
    s = _ghash(h, aad, ct)
    t = (s ^ int.from_bytes(_encrypt_block(rk, j0), "big")).to_bytes(16, "big")
    if decrypt and not _consteq(t, tag):
        raise ValueError("GCM authentication failed – data tampered or wrong key")
    return bytes(out), t


def _consteq(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    r = 0
    for x, y in zip(a, b, strict=False):
        r |= x ^ y
    return r == 0


def py_encrypt(key: bytes, nonce: bytes, pt: bytes, aad: bytes = b"") -> bytes:
    """Pure-Python AES-256-GCM encrypt → ciphertext || tag."""
    ct, tag = _gcm(key, nonce, pt, aad, decrypt=False)
    return ct + tag


def py_decrypt(key: bytes, nonce: bytes, ct_tag: bytes, aad: bytes = b"") -> bytes:
    """Pure-Python AES-256-GCM decrypt (raises ValueError if tag mismatch)."""
    pt, _ = _gcm(key, nonce, ct_tag[:-16], aad, decrypt=True, tag=ct_tag[-16:])
    return pt


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #
class Cipher:
    """AES-256-GCM helper producing compact base64 tokens ``v1:<b64>``."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("AES-256 key must be 32 bytes")
        self._key = key
        self._fast = _AESGCM(key) if _AESGCM is not None else None

    def encrypt(self, plaintext: bytes, aad: bytes = b"") -> str:
        nonce = os.urandom(12)
        if self._fast is not None:
            ct = self._fast.encrypt(nonce, plaintext, aad or None)
        else:
            ct = py_encrypt(self._key, nonce, plaintext, aad)
        return "v1:" + base64.b64encode(nonce + ct).decode("ascii")

    def decrypt(self, token: str, aad: bytes = b"") -> bytes:
        if not token.startswith("v1:"):
            raise ValueError("unknown ciphertext format")
        raw = base64.b64decode(token[3:])
        nonce, ct = raw[:12], raw[12:]
        if self._fast is not None:
            return bytes(self._fast.decrypt(nonce, ct, aad or None))
        return py_decrypt(self._key, nonce, ct, aad)


def load_or_create_key(path: Path) -> bytes:
    """Return the 32-byte data key (env ASTRA_KEY, else key file, else new)."""
    env = os.environ.get("ASTRA_KEY")
    if env:
        return bytes.fromhex(env)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_bytes()
    key = os.urandom(32)
    path.write_bytes(key)
    try:
        os.chmod(path, 0o600)
    except OSError:  # pragma: no cover - Windows
        pass
    return key

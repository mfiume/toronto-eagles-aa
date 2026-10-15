#!/usr/bin/env python3
"""
Password protection for the team's own events.

The schedule page is public, so the team events it carries (practices, dryland,
tournaments) are encrypted with the team password before the page is written,
and decrypted in the browser once a parent enters it. The browser side uses the
Web Crypto API with exactly these parameters (see page_common.SCHEDULE_JS).

PBKDF2 with a high iteration count makes each password guess slow, which is
what protects a published ciphertext. AES-GCM detects a wrong password or a
tampered page instead of producing garbage.
"""

import base64
import hashlib
import os

ITERATIONS = 600_000


def _key(password, salt, iterations):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, 32)


def encrypt(text, password):
    """The text encrypted under the password, as a JSON-ready dict."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt, iv = os.urandom(16), os.urandom(12)
    sealed = AESGCM(_key(password, salt, ITERATIONS)).encrypt(iv, text.encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return {"v": 1, "iter": ITERATIONS, "salt": b64(salt), "iv": b64(iv), "ct": b64(sealed)}


def decrypt(payload, password):
    """The inverse of encrypt; raises on a wrong password. Used by the tests."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    raw = {k: base64.b64decode(payload[k]) for k in ("salt", "iv", "ct")}
    key = _key(password, raw["salt"], payload["iter"])
    return AESGCM(key).decrypt(raw["iv"], raw["ct"], None).decode("utf-8")


class Sealer:
    """
    Encrypts many texts under one password with a single key derivation:
    every event page is sealed with the same salt and key, each with its own
    IV. The browser still derives the key from the page's own payload, so a
    page decrypts on its own; this only spares the hourly build a PBKDF2 run
    per page.
    """

    def __init__(self, password):
        self.salt = os.urandom(16)
        self.key = _key(password, self.salt, ITERATIONS)

    def seal(self, text):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        iv = os.urandom(12)
        sealed = AESGCM(self.key).encrypt(iv, text.encode("utf-8"), None)
        b64 = lambda b: base64.b64encode(b).decode("ascii")
        return {"v": 1, "iter": ITERATIONS, "salt": b64(self.salt), "iv": b64(iv), "ct": b64(sealed)}

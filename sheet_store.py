#!/usr/bin/env python3
"""
The league's game sheets at rest.

The repository is public, so the sheets are kept in it only encrypted with the team password (team_crypto.py), as
game_sheets.sealed.json. The hourly build opens the file with the password, brings it up to date from the league, and
seals it again; the plain sheets exist only in the build's memory. A file left over from before the sheets were sealed
(game_sheets.json) is read once, sealed, and removed.

A password that no longer opens the file is not an error: the sheets are fetched from the league again, which is where
they came from.
"""

import json
import os

import team_crypto

SEALED_FILE = "game_sheets.sealed.json"
LEGACY_FILE = "game_sheets.json"
PASSWORD_ENV = "TEAM_EVENTS_PASSWORD"


def password():
    return os.environ.get(PASSWORD_ENV, "")


def _legacy():
    try:
        with open(LEGACY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def load():
    """Every kept sheet, by game id. Empty when there are none or the sealed file cannot be opened."""
    if os.path.exists(SEALED_FILE):
        if not password():
            return {}
        try:
            with open(SEALED_FILE, encoding="utf-8") as f:
                return json.loads(team_crypto.decrypt(json.load(f), password()))
        except Exception:
            # Counts only: the log of a public repository is public.
            print("Game sheets: the sealed file does not open with the team password; they will be fetched again")
            return {}
    return _legacy()


def migrating():
    """An unsealed file from before sealing is still here, and there is a password to seal it with."""
    return bool(password()) and os.path.exists(LEGACY_FILE)


def save(sheets):
    """Seal the sheets into the repository's file and remove the unsealed one. False when there is no password."""
    if not password():
        return False
    with open(SEALED_FILE, "w", encoding="utf-8") as f:
        json.dump(team_crypto.encrypt(json.dumps(sheets, sort_keys=True), password()), f)
        f.write("\n")
    if os.path.exists(LEGACY_FILE):
        os.remove(LEGACY_FILE)
    return True

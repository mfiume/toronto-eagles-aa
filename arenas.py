#!/usr/bin/env python3
"""
Directions for the rinks the schedule names.

arenas.json is the GTHL's own arena directory (gthlcanada.com/arenas), copied
as published. The schedule names a rink by building and pad ("Iceland 4",
"Al Palladini West", "Vaughan Sports Village B"), so the pad is dropped and the
building is looked up in the directory.

A rink resolves only when its building is in the directory, either under the
same name once generic words are set aside ("Lambton" and "Lambton Arena") or
through RENAMED below. Anything else gets no directions link at all: a wrong
pin is worse than none.
"""

import json
import os
import re
from urllib.parse import quote

DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arenas.json")

# Buildings the schedule calls something other than the directory does. Each
# entry is checked against a source, recorded beside it.
RENAMED = {
    # City of Mississauga, 2026-05-26: Paramount Fine Foods Centre renamed
    # Mississauga Sports and Entertainment Centre from 2026-06-01.
    "mississauga sports and entertainment centre": "Paramount Fine Foods Centre (Formerly Hersey Centre)",
    # The GTHL directory's own map pin for this entry is labelled
    # "Cwench Centre by Canlan Sports".
    "cwench centre etobicoke": "Etobicoke Canlan Ice Sports",
    # NFP took the naming rights to Canlan Sports York, 989 Murray Ross
    # Parkway, in February 2026.
    "nfp athletic centre canlan york": "York Canlan Ice Sports",
    # Spelling differences only: the schedule runs "Pine Point" together, and
    # the directory puts "Vaughan" in brackets.
    "pinepoint": "Pine Point Arena",
    "vaughan sports village": "The (Vaughan) Sports Village",
}


# Words that say what kind of building it is rather than which one.
GENERIC = {"arena", "arenas", "twin", "community", "centre", "center", "recreation", "park", "the"}

# A pad: a trailing number, letter, or side ("4", "B", "West").
PAD = re.compile(r"\s+(\d+|[A-Z]|east|west|north|south)$", re.IGNORECASE)


def _words(name):
    name = re.sub(r"\([^)]*\)", " ", name.lower())  # "(formerly ...)" and similar
    return [w for w in re.findall(r"[a-z0-9]+", name.replace("’", "'"))]


def _key(name):
    return " ".join(w for w in _words(name) if w not in GENERIC)


def building(rink):
    """'Iceland 4' -> 'Iceland'. Drops one pad suffix if there is one."""
    return PAD.sub("", rink.strip())


def _load():
    with open(DIRECTORY, encoding="utf-8") as f:
        return json.load(f)["arenas"]


_ARENAS = _load()
_BY_NAME = {a["name"]: a for a in _ARENAS}
_missing = sorted(set(RENAMED.values()) - set(_BY_NAME))
if _missing:
    raise ValueError(f"RENAMED points at arenas not in {DIRECTORY}: {_missing}")
_BY_KEY = {}
for _a in _ARENAS:
    _BY_KEY.setdefault(_key(_a["name"]), []).append(_a)


def find(rink):
    """The directory entry for a schedule rink name, or None."""
    if not rink:
        return None
    base = building(rink)
    renamed = RENAMED.get(" ".join(_words(base)))
    if renamed:
        return _BY_NAME[renamed]
    matches = _BY_KEY.get(_key(base), [])
    return matches[0] if len(matches) == 1 else None


def address(arena):
    """
    One-line address for a maps search. The postal code is left out: Google
    resolves the street address on its own, and the GTHL's postal codes do not
    always agree with Canada Post's.
    """
    return f"{arena['street']}, {arena['city']}, ON"


def directions_url(rink):
    """A Google Maps directions link for a schedule rink name, or None."""
    arena = find(rink)
    if not arena:
        return None
    return "https://www.google.com/maps/dir/?api=1&destination=" + quote(address(arena))

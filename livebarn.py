#!/usr/bin/env python3
"""
LiveBarn links for games the GTHL does not list: exhibitions, preseason and
tournament games from the team calendar.

A LiveBarn link is https://livebarn.com/en/video/{surface}/{date}/{HH:MM}: the
camera on one ice pad, at the date and start time. The GTHL publishes one for
each league game, and a pad's surface number does not change, so every league
link teaches us a pad: "Lambton" is 4198, "Scotiabank Pond 2" is 4088.

livebarn_surfaces.json keeps what has been learned, {GTHL rink name: surface},
so a pad stays known after its games leave the scrape window. Running this
file updates it from schedule.json and season_schedule.json.

A team-calendar game gets a link only when its venue is a known pad without
doubt: the same building (arenas.py) and, where the building has more than one
pad, the same pad named in the venue. Anything less gets no link; a link to the
wrong rink's camera is worse than none.
"""

import json
import os
import re

import arenas
import season_schedule

SURFACES_FILE = "livebarn_surfaces.json"
LINK = re.compile(r"^https://livebarn\.com/en/video/(\d+)/")

# A pad named in a venue: "Rink 1", "Pad B", "Arena 2", or a bare trailing
# number, letter or side.
VENUE_PAD = re.compile(r"(?:\b(?:rink|pad|ice|arena|surface)\s*)?\b(\d+|[a-z]|east|west|north|south)$",
                       re.IGNORECASE)


def load(path=SURFACES_FILE):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("surfaces", {})


def learn(rows, games, known=None):
    """{rink: surface} from schedule rows and accumulated season games."""
    known = dict(known or {})
    pairs = [(g.get("Arena", ""), g.get("Stream", "")) for g in rows]
    pairs += [(g.get("arena", ""), g.get("stream", "")) for g in games]
    for rink, url in pairs:
        m = LINK.match((url or "").strip())
        if rink and m:
            known[rink] = m.group(1)
    return known


def update():
    rows = games = []
    if os.path.exists("schedule.json"):
        with open("schedule.json", encoding="utf-8") as f:
            rows = json.load(f).get("schedule", [])
    if os.path.exists(season_schedule.SEASON_FILE):
        with open(season_schedule.SEASON_FILE, encoding="utf-8") as f:
            games = json.load(f).get("games", [])
    known = learn(rows, games, load())
    with open(SURFACES_FILE, "w", encoding="utf-8") as f:
        json.dump({"note": "LiveBarn surface per GTHL rink, learned from the GTHL's own links",
                   "surfaces": dict(sorted(known.items()))}, f, indent=1)
    print(f"LiveBarn: {len(known)} pads known")
    return known


def _pad(text):
    m = VENUE_PAD.search(text.strip())
    return m.group(1).lower() if m else None


def _street(text):
    """'4100 Dundas St W York, ON' -> ('4100', 'dundas'): enough to tell buildings apart."""
    m = re.match(r"\s*(\d+)\s+([A-Za-z]+)", text or "")
    return (m.group(1), m.group(2).lower()) if m else None


def _arena_for_venue(venue, address):
    building = re.split(r"\s+[-·]\s+", venue or "")[0]
    arena = arenas.find(building) if building else None
    if arena:
        return arena
    street = _street(address)
    if street:
        hits = [a for a in arenas._ARENAS if _street(a.get("street")) == street]
        if len(hits) == 1:
            return hits[0]
    return None


def surface_for(venue, address, known):
    """The surface for a team-calendar venue, or None unless it is certain."""
    arena = _arena_for_venue(venue, address)
    if not arena:
        return None
    pads = {rink: s for rink, s in known.items()
            if (found := arenas.find(rink)) and found["name"] == arena["name"]}
    if not pads:
        return None
    parts = re.split(r"\s+[-·]\s+", venue or "")
    wanted = _pad(parts[1]) if len(parts) > 1 else None
    if wanted is None and arenas.building(parts[0]) != parts[0].strip():
        wanted = _pad(parts[0])
    for rink, surface in pads.items():
        pad = arenas.building(rink) != rink and _pad(rink)
        if wanted and pad == wanted:
            return surface
        if not wanted and not pad:
            return surface   # A one-pad building: the rink is the building.
    return None


def url(surface, start):
    """The LiveBarn link for a pad at a start time (a naive local datetime)."""
    return f"https://livebarn.com/en/video/{surface}/{start:%Y-%m-%d}/{start:%H:%M}"


if __name__ == "__main__":
    update()

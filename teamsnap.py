#!/usr/bin/env python3
"""
The team's own calendar from TeamSnap: practices, dryland, tournaments and the
games the GTHL does not list (exhibition, preseason, tournament games).

The feed is private. Its URL comes from the TEAMSNAP_ICS_URL secret and is never
printed, and what this writes, team_events.json, is never committed: the
schedule page carries the team events only encrypted with the team password
(see team_crypto.py).

Only fields a family needs are kept: when, what, where, arrival time and what
to wear. TeamSnap's free-text notes are dropped, since they can hold names and
phone numbers.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime

OUTPUT = "team_events.json"

# A summary is "Toronto Eagles U11 AA - Eagles practice" or
# "Toronto Eagles U11 AA regular game at Mississauga Terriers".
TEAM_PREFIX = re.compile(r"^Toronto Eagles U\d+ AA\s*-?\s*", re.IGNORECASE)
OPPONENT = re.compile(r"\b(vs|at)\s+(.+)$", re.IGNORECASE)


def unfold(text):
    """iCalendar folds long lines with a leading space; undo it."""
    return re.sub(r"\r?\n[ \t]", "", text.replace("\r\n", "\n"))


def unescape(value):
    return (value.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\"))


def parse_ics(text):
    """Every VEVENT as {property: value}, parameters dropped."""
    events = []
    for block in re.findall(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", unfold(text), re.S):
        fields = {}
        for line in block.split("\n"):
            key, _, value = line.partition(":")
            fields.setdefault(key.split(";")[0].upper(), value)
        events.append(fields)
    return events


def parse_time(value):
    """TeamSnap writes local Toronto times (TZID=America/Toronto)."""
    value = value.strip()
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"):
        try:
            return datetime.strptime(value.rstrip("Z"), fmt)
        except ValueError:
            continue
    return None


def kind_of(title):
    """practice, dryland, tournament, game or event."""
    t = title.lower()
    if "dryland" in t:
        return "dryland"
    if "practice" in t:
        return "practice"
    if OPPONENT.search(title):
        return "game"
    if "tournament" in t:
        return "tournament"
    return "event"


def game_label(title):
    """Exhibition, Preseason, Tournament or League, from how the game is named."""
    t = title.lower()
    if "exhibition" in t:
        return "Exhibition"
    if "pre season" in t or "preseason" in t or "pre-season" in t:
        return "Preseason"
    if "tournament" in t:
        return "Tournament"
    return "League"


def details(description):
    """Venue, arrival time and uniform from the labelled lines; nothing else."""
    text = unescape(description)
    venue = re.search(r"^\s*Location:\s*(.+)$", text, re.M)
    arrive = re.search(r"Arrival Time:\s*([0-9]{1,2}:[0-9]{2}\s*[AP]M)", text, re.I)
    uniform = re.search(r"^\s*Uniform:\s*([^(\n]+)", text, re.M)
    # A few events put the dress code before the arrival time without a label,
    # e.g. "Gym clothes  (Arrival Time: ...)".
    wear = uniform.group(1).strip() if uniform else None
    if not wear:
        bare = re.search(r"^\s*([A-Za-z][^:(\n]{2,40}?)\s*\(Arrival Time", text, re.M)
        if bare and not re.search(r"presence|absence|teamsnap|ice", bare.group(1), re.I):
            wear = bare.group(1).strip()
    return {
        "venue": venue.group(1).strip() if venue else None,
        "arrive": re.sub(r"\s+", " ", arrive.group(1)).upper() if arrive else None,
        "wear": wear,
    }


def clean_address(location):
    location = unescape(location or "").strip()
    return None if not location or location.upper() in ("TBC", "TBD") else location


def to_event(fields):
    start, end = parse_time(fields.get("DTSTART", "")), parse_time(fields.get("DTEND", ""))
    if not start:
        return None
    title = TEAM_PREFIX.sub("", unescape(fields.get("SUMMARY", "")).strip()).strip(" -")
    kind = kind_of(title)
    event = {
        "uid": fields.get("UID", ""),
        "start": start.isoformat(timespec="minutes"),
        "end": end.isoformat(timespec="minutes") if end else None,
        "kind": kind,
        "title": title,
        "address": clean_address(fields.get("LOCATION")),
        **details(fields.get("DESCRIPTION", "")),
    }
    # A placeholder with no length (08:00-08:00) has no real start time.
    event["timed"] = bool(end and end > start)
    if kind == "game":
        side, opponent = OPPONENT.search(title).groups()
        event["opponent"] = opponent.strip()
        event["home"] = side.lower() == "vs"
        event["label"] = game_label(title)
    return event


def events_from_ics(text):
    events = [e for e in (to_event(f) for f in parse_ics(text)) if e]
    return sorted(events, key=lambda e: e["start"])


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def main():
    # For local testing: python teamsnap.py path/to/calendar.ics
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    else:
        url = os.environ.get("TEAMSNAP_ICS_URL", "").strip()
        if not url:
            print("TEAMSNAP_ICS_URL is not set; skipping team events")
            return
        try:
            text = fetch(url)
        except OSError as exc:
            # Never print the URL: it is the key to the team calendar.
            print(f"Could not fetch the team calendar ({type(exc).__name__}); keeping the last copy")
            return
    events = events_from_ics(text)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"fetched": datetime.now().isoformat(timespec="minutes"), "events": events}, f)
    counts = {}
    for e in events:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
    # Counts only: the log of a public repository is public.
    print(f"Team calendar: {len(events)} events {counts}")


if __name__ == "__main__":
    main()

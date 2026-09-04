#!/usr/bin/env python3
"""
The season-long schedule, and the stable game ids the stat tracker needs.

`schedule.json` is a *window* onto the schedule: SCHEDULE_DAYS_BACK days behind
to SCHEDULE_DAYS_AHEAD ahead. That is the right shape for a page showing what is
coming up, but it means a game disappears about a week after it is played, and
its rows carry no identifier, so nothing downstream can say "this is the game I
tracked" across two scrapes.

This module fixes both, without touching how the pages are generated:

  season_schedule.json   every game we have ever seen this season, accumulating
  eagles_schedule.json   just our games, parsed into the fields a client wants

Games are keyed by a deterministic id built from the date and the two teams.
Deliberately *not* the start time: ice times slide by twenty minutes all the
time and that must not orphan a tracked game. A fixture moved to a different
date really is a different fixture, and gets a new id.

Nothing is ever deleted. A game that ages out of the scrape window is simply
retained. A game that is inside the window but stops being listed is marked
`not_listed` rather than dropped, because a cancellation and a scraper failure
look identical from here and only a human can tell them apart.
"""

import json
import os
import re
from datetime import datetime, timezone

import config

SEASON_FILE = "season_schedule.json"
EAGLES_FILE = "eagles_schedule.json"

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def slug(name):
    """'West Mall Lightning' -> 'west-mall-lightning'."""
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def iso_date(raw):
    """'12-Oct-2026 Mon' -> '2026-10-12', or '' if it will not parse."""
    match = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", (raw or "").strip())
    if not match:
        return ""
    day, month, year = match.groups()
    number = MONTHS.get(month.title())
    return f"{year}-{number:02d}-{int(day):02d}" if number else ""


def iso_time(raw):
    """'7:10 PM' -> '19:10', or '' if it will not parse."""
    match = re.match(r"(\d{1,2}):(\d{2})\s*([AaPp])\.?[Mm]", (raw or "").strip())
    if not match:
        return ""
    hour, minute, meridiem = match.groups()
    hour = int(hour) % 12
    if meridiem.lower() == "p":
        hour += 12
    return f"{hour:02d}:{minute}"


def game_id(game):
    """
    Stable id for a scheduled game: '2026-10-18_west-mall-lightning_at_toronto-eagles'.

    Date plus the two teams. No start time, so a rescheduled puck drop on the
    same day keeps the same id and any stats already tracked against it.

    The cost of leaving the time out is that the same two teams playing twice on
    one day would collide. That does not happen in GTHL league or playoff play,
    which is all this feed carries, and `merge()` warns rather than silently
    overwriting if it ever does.
    """
    date = iso_date(game.get("Date", ""))
    return f"{date}_{slug(game.get('Away'))}_at_{slug(game.get('Home'))}"


def parse_score(raw):
    """
    The score as {'away': n, 'home': n}, or None if the game has not been played.

    The GTHL writes an unplayed game as a bare ':'. The column sits between Away
    and Home in the table, so it is read as away:home. If a played row ever
    proves otherwise the raw string is kept alongside, so nothing is lost.
    """
    match = re.match(r"^\s*(\d+)\s*:\s*(\d+)\s*$", raw or "")
    if not match:
        return None
    return {"away": int(match.group(1)), "home": int(match.group(2))}


def enrich(game):
    """A scraped row plus the fields a client should not have to derive itself."""
    away = game.get("Away", "")
    home = game.get("Home", "")
    score = parse_score(game.get("Score", ""))

    if config.TEAM_NAME == home:
        side = "home"
    elif config.TEAM_NAME == away:
        side = "away"
    else:
        side = None

    result = None
    if score and side:
        ours, theirs = (score[side],
                        score["away" if side == "home" else "home"])
        result = "W" if ours > theirs else "L" if ours < theirs else "T"

    return {
        "id": game_id(game),
        "date": iso_date(game.get("Date", "")),
        "time": iso_time(game.get("Time", "")),
        "away": away,
        "home": home,
        "arena": game.get("Arena", ""),
        "type": game.get("Type", ""),
        "division": game.get("Div/Cat", ""),
        "score": score,
        "score_raw": game.get("Score", ""),
        "status": "final" if score else "scheduled",
        "is_eagles": side is not None,
        "eagles_side": side,
        "opponent": (away if side == "home" else home) if side else None,
        "result": result,
    }


def load_existing(path=SEASON_FILE):
    """Whatever we have accumulated so far, keyed by game id."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        # A corrupt accumulator must not take the run down, but starting over
        # silently would quietly lose the season, so say so loudly.
        print(f"WARNING: could not read {path} ({e}); starting a new accumulator")
        return {}
    return {g["id"]: g for g in data.get("games", []) if g.get("id")}


def merge(scraped, filters, existing=None, now=None):
    """
    Fold a freshly scraped window into everything seen before.

    Returns the merged games, newest id order aside, sorted by date and time.
    """
    existing = dict(load_existing() if existing is None else existing)
    now = (now or datetime.now(timezone.utc)).isoformat()

    seen = {}
    for row in scraped:
        game = enrich(row)
        if not game["date"]:
            print(f"Skipping a row with an unparseable date: {row.get('Date')!r}")
            continue
        clash = seen.get(game["id"])
        if clash and clash != game["time"]:
            # Same two teams, same day, two puck drops. Impossible in league
            # play, so say so loudly rather than quietly keeping one of them.
            print(f"WARNING: two games share the id {game['id']} "
                  f"({clash} and {game['time']}); keeping the later row")
        seen[game["id"]] = game["time"]
        previous = existing.get(game["id"], {})
        game["first_seen"] = previous.get("first_seen", now)
        game["last_seen"] = now
        existing[game["id"]] = game

    # A game inside the window that the site stopped listing is flagged, not
    # dropped: a cancellation and a scraper hiccup are indistinguishable here.
    window_from = iso_date(filters.get("from_date", ""))
    window_to = iso_date(filters.get("to_date", ""))
    for gid, game in existing.items():
        if gid in seen or not window_from or not window_to:
            continue
        if window_from <= game.get("date", "") <= window_to:
            if game.get("status") != "not_listed":
                game["status"] = "not_listed"
                game["missing_since"] = now

    return sorted(existing.values(), key=lambda g: (g["date"], g["time"]))


def write(scraped, filters, timestamp=None):
    """Update both files from a freshly scraped window. Returns the merged games."""
    games = merge(scraped, filters)
    stamp = timestamp or datetime.now(timezone.utc).isoformat()

    header = {
        "team": config.TEAM_NAME,
        "season": config.SEASON,
        "division": config.DIVISION,
        "category": config.CATEGORY,
        "region": config.REGION,
    }

    with open(SEASON_FILE, "w", encoding="utf-8") as f:
        json.dump({**header, "timestamp": stamp, "games": games},
                  f, indent=2, ensure_ascii=False)

    ours = [g for g in games if g["is_eagles"]]
    with open(EAGLES_FILE, "w", encoding="utf-8") as f:
        json.dump({**header, "timestamp": stamp, "games": ours},
                  f, indent=2, ensure_ascii=False)

    played = sum(1 for g in ours if g["status"] == "final")
    print(f"Season schedule: {len(games)} games ever seen, "
          f"{len(ours)} ours ({played} played)")
    return games


def main():
    """Rebuild the accumulators from the current schedule.json."""
    with open("schedule.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("error"):
        print(f"schedule.json holds an error, leaving the accumulators alone: "
              f"{data['error']}")
        return
    write(data.get("schedule", []), data.get("filters", {}), data.get("timestamp"))


if __name__ == "__main__":
    main()

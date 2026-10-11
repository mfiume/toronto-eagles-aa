#!/usr/bin/env python3
"""
Cache the club logos the standings and schedule scrapes point at, so the
pages serve them from GitHub Pages instead of hotlinking agilex.ca.

Each logo is saved as assets/logos/<team-slug>.png, keyed by team name rather
than by the GTHL's three-letter code, because the schedule only knows names.
A logo already on disk is never fetched again. A failed download is reported
and skipped: the pages fall back to the team's initials, so a missing logo is
never a reason to fail the run.
"""

import json
import os
import urllib.request

from season_schedule import slug

LOGO_DIR = os.path.join("assets", "logos")


def logo_path(team):
    """Where a team's cached logo lives, whether or not it exists yet."""
    return os.path.join(LOGO_DIR, f"{slug(team)}.png")


def known_logos():
    """
    (team, url) for every logo the scrapes recorded: one per standings row,
    and both sides of every schedule row, which also covers the other region.
    """
    pairs = []
    for path, read in (
        ("standings.json", lambda d: [(r.get("Team"), r.get("Logo")) for r in d.get("standings", [])]),
        ("schedule.json", lambda d: [pair for g in d.get("schedule", []) for pair in (
            (g.get("Away"), g.get("AwayLogo")), (g.get("Home"), g.get("HomeLogo")))]),
    ):
        try:
            with open(path, encoding="utf-8") as f:
                pairs += read(json.load(f))
        except (OSError, ValueError):
            continue
    return pairs


def fetch_missing(pairs):
    """Download each logo that is not cached yet."""
    os.makedirs(LOGO_DIR, exist_ok=True)
    fetched = []
    for team, url in pairs:
        if not team or not url or os.path.exists(logo_path(team)):
            continue
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                data = response.read()
        except OSError as exc:
            print(f"Could not fetch the logo for {team}: {exc}")
            continue
        if not data.startswith(b"\x89PNG"):
            print(f"Skipping the logo for {team}: {url} is not a PNG")
            continue
        with open(logo_path(team), "wb") as f:
            f.write(data)
        fetched.append(team)
    return fetched


def main():
    fetched = fetch_missing(known_logos())
    print(f"Fetched {len(fetched)} new logo(s)" + (f": {', '.join(fetched)}" if fetched else ""))


if __name__ == "__main__":
    main()

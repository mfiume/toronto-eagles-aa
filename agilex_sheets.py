#!/usr/bin/env python3
"""
The league's official game sheets for our games (Agilex SportTrek), kept sealed with the team password as game_sheets.sealed.json (sheet_store.py).

A team official signs in with a Hockey ID and a personal code. The sheet of a game is two JSON calls the league's own
pages make. The sign-in comes from the environment (AGILEX_HOCKEY_ID, AGILEX_PERSONAL_CODE, AGILEX_LEAGUE), never from a
file in this repository. Without it the script does nothing and the existing file is left as it is.

This site is public, so only team-level figures are kept: the goals, penalties and timeouts with their period,
clock and team, and the score by period. Player names, jersey numbers and rosters are dropped here, before anything is
written, so they cannot reach the repository. What is kept is sealed as well, so the sheets are not readable there.
"""

import json
import os
import sys
import urllib.error
import urllib.request

import config
import season_schedule
import sheet_store

ORIGIN = os.environ.get("AGILEX_ORIGIN", "https://www.agilex.ca/SportTrek/AppService")


def _request(path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(ORIGIN + path, data=data, headers=headers, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login():
    reply = _request("/Login", body={
        "client": os.environ.get("AGILEX_LEAGUE", "GTHL"), "isAdmin": False, "username": "", "password": "",
        "hockeyID": os.environ["AGILEX_HOCKEY_ID"], "personalCode": os.environ["AGILEX_PERSONAL_CODE"],
    })
    if not reply.get("token"):
        raise RuntimeError("the league did not accept the sign-in")
    return reply["token"], str(reply.get("fullTeamID", ""))


def clock_seconds(text):
    """'06:19' -> 379, or None."""
    try:
        m, s = str(text).strip().split(":")
        return int(m) * 60 + int(s)
    except ValueError:
        return None


def clock_text(seconds):
    return f"{seconds // 60}:{seconds % 60:02d}"


def public_sheet(raw):
    """What is safe to publish from the league's JSON for one game."""
    gi = raw.get("gameInfo") or {}
    side = lambda team_id: "home" if team_id == gi.get("homeID") else "away"

    def moments(rows, clock_field="gameTime"):
        out = []
        for row in rows or []:
            seconds = clock_seconds(row.get(clock_field) or row.get("gameTime"))
            try:
                period = int(row.get("period"))
            except (TypeError, ValueError):
                continue
            if seconds is None or not period:
                continue
            out.append((period, seconds, side(row.get("teamID")), row))
        return sorted(out, key=lambda m: (m[0], -m[1]))

    goals = [{"period": p, "clock": clock_text(s), "side": t, "kind": str(r.get("scoreType") or "")}
             for p, s, t, r in moments(raw.get("scoreStats"))]
    penalties = [{"period": p, "clock": clock_text(s), "side": t, "code": str(r.get("pecCode") or ""),
                  "minutes": int(r.get("min") or 0)}
                 for p, s, t, r in moments(raw.get("penaltyStats"), "off")]
    timeouts = [{"period": p, "clock": clock_text(s), "side": t} for p, s, t, _ in moments(raw.get("timeoutStats"))]
    periods = range(1, max([3] + [m["period"] for m in goals + penalties + timeouts]) + 1)
    by_period = [{"period": n, "home": sum(1 for g in goals if g["period"] == n and g["side"] == "home"),
                  "away": sum(1 for g in goals if g["period"] == n and g["side"] == "away")} for n in periods]
    return {
        "home": gi.get("home", ""), "away": gi.get("visitor", ""),
        "final": {"home": sum(p["home"] for p in by_period), "away": sum(p["away"] for p in by_period)},
        "periods": by_period, "goals": goals, "penalties": penalties, "timeouts": timeouts,
    }


def main():
    if sheet_store.migrating():
        sheet_store.save(sheet_store.load())
        print("Game sheets sealed")
    if not (os.environ.get("AGILEX_HOCKEY_ID") and os.environ.get("AGILEX_PERSONAL_CODE")):
        print("League sign-in not set: game sheets left as they were")
        return 0
    with open(season_schedule.EAGLES_FILE, encoding="utf-8") as f:
        games = [g for g in json.load(f)["games"] if g.get("status") == "final"]
    sheets = sheet_store.load()
    token, _ = login()
    changed = 0
    for g in games:
        y, m, d = g["date"].split("-")
        listed = _request(f"/GetGamesListWithInfo?param={m}/{d}/{y}", token).get("games") or []
        ours = [x for x in listed if config.TEAM_NAME in (x.get("homeName") or x.get("home"), x.get("visitorName") or x.get("visitor"))]
        if not ours:
            continue
        raw = _request(f"/GetGameData?gameID={ours[0]['gameID']}&param={m}/{d}/{y}", token)
        if not raw.get("gameInfo"):
            continue
        sheet = public_sheet(raw)
        if sheets.get(g["id"]) != sheet:
            sheets[g["id"]] = sheet
            changed += 1
    # Sealing writes a new file every time, so it is only written when there is something new to keep.
    if changed or not os.path.exists(sheet_store.SEALED_FILE):
        if not sheet_store.save(sheets):
            print("Game sheets not kept: no team password to seal them with")
            return 0
    print(f"Game sheets: {len(sheets)} kept, {changed} new or changed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (urllib.error.URLError, RuntimeError, KeyError) as exc:
        # The league being unreachable must not break the hourly build; the file already there is kept.
        print(f"Game sheets not refreshed: {exc}")
        sys.exit(0)

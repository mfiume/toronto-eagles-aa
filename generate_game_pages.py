#!/usr/bin/env python3
"""
A page for every league game of the season: game-<id>.html, reached by tapping
a game on the schedule or a team page. The id is season_schedule.game_id, so a
game keeps its page when its start time moves.

Like the team pages, it is built hourly from what the site already keeps (the
standings and the season's games) and states nothing it cannot work out. The
team calendar is private and never reaches these pages: arrival times and
jerseys stay on the schedule, behind the team log-in.

What a page has, top to bottom:
  the matchup: both crests and names (each a link to the team's page), and
               the score, LIVE, or when it starts
  watch and go: LiveBarn, and directions to the rink
  when and where: the full date, the rink and its address
  tale of the tape: the two teams side by side, the better figure in bold
  season series: every meeting of the two this season, each linking on
"""

import glob
import os
from datetime import datetime
from html import escape

import arenas
import config
import page_common
from generate_schedule_html import (PLAY_ICON, aware, countdown, game_page, game_row, live_flag,
                                    maps_link, stream_state, team_name_html)
from generate_team_pages import (all_games, division_rank, form_chips, number, ordinal,
                                 side_of, team_games)


def standings_row(standings, team):
    return next((r for r in standings if r.get("Team") == team), None)


# --- Sections -------------------------------------------------------------------

def status(g, today, now):
    """The line above the matchup: Final, LIVE, or when it starts."""
    start = aware(g["start"])
    if g["score"]:
        return '<span class="match-status">Final</span>'
    state = stream_state(start, now) if start is not None else "upcoming"
    if state == "live":
        return live_flag(start, now)
    if state == "rewatch":
        return '<span class="match-status">Awaiting final score</span>'
    return f'<span class="match-status upcoming">{escape(countdown(g["day"], today))}</span>'


def matchup(g, standings, today, now):
    row = g["row"]
    away, home = row.get("Away", ""), row.get("Home", "")
    ours = config.TEAM_NAME in (away, home)

    def side(team, role):
        st = standings_row(standings, team)
        record = ""
        if st:
            played = str(st.get("GP", "0")).strip() not in ("", "0")
            record = f'{page_common.place_label(st)} · {st.get("W-L-T") if played else "0-0-0"}'
        return f"""<div class="match-team{' us' if team == config.TEAM_NAME else ''}">
                        {page_common.team_logo(team, st.get('Logo') if st else None)}
                        <span class="match-name">{team_name_html(team)}</span>
                        <span class="match-role">{role}</span>
                        <span class="match-record">{escape(record)}</span>
                    </div>"""

    if g["score"]:
        a, h = g["score"]["away"], g["score"]["home"]
        middle = (f'<div class="match-score{" decided" if a != h else ""}"><span class="{"win" if a > h else ""}">{a}</span>'
                  f'<span class="dash">–</span><span class="{"win" if h > a else ""}">{h}</span></div>')
    else:
        middle = (f'<div class="match-time"><span>{escape(row.get("Time", "") or "TBA")}</span>'
                  f'<span class="match-date">{g["day"].strftime("%a, %b")} {g["day"].day}</span></div>')
    result = ""
    if g["score"] and ours:
        r = side_of(g, config.TEAM_NAME)["result"]
        result = (f'<span class="match-result result-{r.lower()}">'
                  f'{ {"W": "Eagles win", "L": "Eagles loss", "T": "Tie"}[r] }</span>')
    return f"""
                <section class="match-hero{' is-ours' if ours else ''}">
                    <div class="match-top"><span>{escape(page_common.division_label())} · League game</span>
                        {status(g, today, now)}</div>
                    <div class="match-face">
                    {side(away, "Away")}
                    <div class="match-middle">{middle}{result}</div>
                    {side(home, "Home")}
                    </div>
                </section>
"""


def actions(g, now):
    row = g["row"]
    buttons = ""
    url = (row.get("Stream") or "").strip()
    start = aware(g["start"])
    if url.startswith("https://livebarn.com/") and start is not None:
        state = stream_state(start, now)
        text = {"upcoming": "Watch live on LiveBarn", "live": "Live now on LiveBarn",
                "rewatch": "Rewatch on LiveBarn"}[state]
        buttons += (f'<a class="match-btn watch is-{state}" href="{escape(url)}" target="_blank" '
                    f'rel="noopener noreferrer">{PLAY_ICON}<span>{text}</span></a>')
    rink = row.get("Arena", "")
    google = arenas.directions_url(rink)
    if google and not g["score"]:
        buttons += maps_link(google, arenas.apple_directions_url(rink), "match-btn", "Directions",
                             f"Directions to {rink}")
    return f'\n                <div class="match-actions">{buttons}</div>\n' if buttons else ""


def where_when(g):
    row = g["row"]
    rink = row.get("Arena", "")
    arena = arenas.find(rink)
    place = escape(arena["name"] if arena else rink)
    addr = escape(arenas.address(arena)) if arena else ""
    google = arenas.directions_url(rink)
    if google:
        place = maps_link(google, arenas.apple_directions_url(rink), "match-place", arena["name"],
                          f"Directions to {arena['name']}, {arenas.address(arena)}")
    when = f'{g["day"].strftime("%A, %B")} {g["day"].day}, {g["day"].year}'
    if row.get("Time"):
        when += f' · {escape(row["Time"])}'
    rows = [("When", when), ("Where", place + (f'<span class="match-sub">{addr}</span>' if addr else "")),
            # The rink, when it says more than the arena's name ("Pond 2").
            ("Rink", escape(rink)) if arena and not arena["name"].lower().startswith(rink.lower()) else None]
    cells = "".join(f'<div class="fact"><span class="fact-label">{k}</span><span class="fact-value">{v}</span></div>'
                    for k, v in (r for r in rows if r))
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>When and where</h3></div>
                    <div class="facts">{cells}</div>
                </section>
"""


def tale_of_the_tape(g, standings, games):
    away, home = g["row"].get("Away", ""), g["row"].get("Home", "")
    sa, sh = standings_row(standings, away), standings_row(standings, home)
    if not sa or not sh:
        return ""

    def played(st):
        return str(st.get("GP", "0")).strip() not in ("", "0")

    lines = []

    def line(label, a, h, better=None):
        """`better`: 'high' or 'low' to bold the better side when both are numbers."""
        cls_a = cls_h = ""
        na, nh = number(str(a).lstrip("+")), number(str(h).lstrip("+"))
        if better and na is not None and nh is not None and na != nh:
            a_wins = na > nh if better == "high" else na < nh
            cls_a, cls_h = (" better", "") if a_wins else ("", " better")
        lines.append(f'<div class="tape-row"><span class="tape-val{cls_a}">{a}</span>'
                     f'<span class="tape-label">{label}</span><span class="tape-val right{cls_h}">{h}</span></div>')

    line("Place", page_common.place_label(sa), page_common.place_label(sh))
    line("Record", sa.get("W-L-T") if played(sa) else "0-0-0", sh.get("W-L-T") if played(sh) else "0-0-0")
    line("Points", sa.get("PTS") or "0", sh.get("PTS") or "0", "high")
    if played(sa) or played(sh):
        line("Win %", sa.get("WIN%") or "–", sh.get("WIN%") or "–", "high")
        line("Goals for / game", sa.get("GFA") or "–", sh.get("GFA") or "–", "high")
        line("Goals against / game", sa.get("GAA") or "–", sh.get("GAA") or "–", "low")
        line("Road / home record", sa.get("Away") or "0-0-0", sh.get("Home") or "0-0-0")
        streak_a, streak_h = str(sa.get("Streak") or "–"), str(sh.get("Streak") or "–")
        line("Streak", escape(streak_a), escape(streak_h))
    fa = [x for x in team_games(games, away) if x["score"] and x["day"] < g["day"]]
    fh = [x for x in team_games(games, home) if x["score"] and x["day"] < g["day"]]
    if fa or fh:
        lines.append(f'<div class="tape-row"><span class="tape-val form">{form_chips(fa, away) or "–"}</span>'
                     f'<span class="tape-label">Last 5 before</span>'
                     f'<span class="tape-val right form">{form_chips(fh, home) or "–"}</span></div>')
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Tale of the tape</h3><span>From today's standings</span></div>
                    <div class="tape">
                        <div class="tape-row tape-head"><span class="tape-val">{team_name_html(away)}</span>
                            <span class="tape-label"></span><span class="tape-val right">{team_name_html(home)}</span></div>
                        {"".join(lines)}
                    </div>
                </section>
"""


def series(g, games, now):
    away, home = g["row"].get("Away", ""), g["row"].get("Home", "")
    meetings = [x for x in games if {x["row"].get("Away"), x["row"].get("Home")} == {away, home}]
    others = [x for x in meetings if x is not g]
    played = [x for x in meetings if x["score"]]
    if played:
        wa = sum(side_of(x, away)["result"] == "W" for x in played)
        wh = sum(side_of(x, home)["result"] == "W" for x in played)
        ties = len(played) - wa - wh
        summary = f"{escape(away.split()[-1])} {wa} · {escape(home.split()[-1])} {wh}" + (f" · {ties} tied" if ties else "")
    else:
        summary = "Yet to be decided"
    if not others:
        note = '<p class="team-empty">Their only meeting this season.</p>'
        rows = ""
    else:
        note, rows = "", ""
        for x in meetings:
            html = game_row(x["row"], x["day"], config.TEAM_NAME.lower(), None, aware(x["start"]), now)
            if x is g:
                html = html.replace('class="game', 'class="game is-current', 1)
            rows += html
        rows = f'                    <div class="week-games">\n{rows}                    </div>\n'
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Season series</h3><span>{summary}</span></div>
                    {note}<div class="team-games">
{rows}                    </div>
                </section>
"""


# --- Assembly -------------------------------------------------------------------

def page(g, standings, games, timestamp, today, now):
    row = g["row"]
    title = f"{row.get('Away', '')} at {row.get('Home', '')}"
    body = matchup(g, standings, today, now)
    body += actions(g, now)
    body += where_when(g)
    body += tale_of_the_tape(g, standings, games)
    body += series(g, games, now)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)} - {g['day'].strftime('%b')} {g['day'].day} - {config.SITE_TITLE}</title>
{page_common.FONT_LINK}
{page_common.FAVICON_LINKS}
    <style>
{page_common.PAGE_CSS}{page_common.TEAM_CSS}{page_common.GAME_CSS}    </style>
</head>
<body>
    <div class="container">
{page_common.masthead("schedule.html", page_common.division_label(), page_common.season_label())}

        <div class="content">
            <div class="team-page">
                <a class="team-back" href="schedule.html">&#8249; Schedule</a>
{body}            </div>
{page_common.freshness(timestamp)}        </div>

{page_common.page_end()}    </div>
{page_common.SCHEDULE_JS}</body>
</html>
"""


def generate(today=None):
    import json
    try:
        with open("standings.json", encoding="utf-8") as f:
            standings_data = json.load(f)
        with open("schedule.json", encoding="utf-8") as f:
            schedule_data = json.load(f)
    except FileNotFoundError as exc:
        print(f"Game pages skipped: {exc.filename} not found")
        return []
    standings = page_common.rank_standings(standings_data.get("standings", []))
    now = datetime.now(page_common.TORONTO)
    today = today or now.date()
    games = all_games(schedule_data.get("schedule", []))
    written = {}
    for g in games:
        name = game_page(g["row"])
        with open(name, "w", encoding="utf-8") as f:
            f.write(page(g, standings, games, schedule_data.get("timestamp", ""), today, now))
        written[name] = True
    # A game the GTHL no longer lists takes its page with it.
    for stale in set(glob.glob("game-*.html")) - set(written):
        os.remove(stale)
    print(f"Generated {len(written)} game pages")
    return list(written)


if __name__ == "__main__":
    generate()

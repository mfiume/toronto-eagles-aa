#!/usr/bin/env python3
"""
A page for every team in the division: team-<slug>.html, reached by tapping a
team in the standings.

Everything on it comes from data the site already keeps: the standings row,
and every game of the season from the schedule plus the season accumulator
(season_schedule.json), which remembers games after the GTHL's scrape window
has moved past them. Nothing is estimated: a figure that cannot be worked out
yet ("biggest win" before a win) is left out rather than shown as zero.

What a page has, top to bottom:
  the team: crest, name, place in the standings, record, streak
  form: the last five results
  scouting: offence and defence ranked against the division, goal
            difference, home and away, biggest win
  points path: how the points have built up, against the most possible
  versus the Eagles: the season series and every meeting (on the Eagles'
            own page, the Eagles' record against every opponent)
  next game, results and what is still to come, as the schedule shows games
"""

import glob
import json
import os
from datetime import datetime
from html import escape

import config
import page_common
from generate_schedule_html import (countdown_attr, aware, clock, countdown, directions_link, format_score,
                                    game_row, parse_game_date, parse_game_time, season_rows,
                                    watch_link, next_game_card, game_page)
from season_schedule import parse_score, slug


def page_name(team):
    """'Mississauga Beast' -> 'team-mississauga-beast.html'."""
    return f"team-{slug(team)}.html"


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def number(value):
    """A standings figure as a float, or None for a blank or a dash."""
    try:
        return float(str(value).strip())
    except ValueError:
        return None


# --- The season's games, from one team's side ---------------------------------

def all_games(schedule):
    """Every league game of the season, in schedule-row form, oldest first."""
    rows = schedule + season_rows(schedule)
    games = []
    for g in rows:
        day = parse_game_date(g.get("Date", ""))
        if not day:
            continue
        t = parse_game_time(g.get("Time", ""))
        start = datetime.combine(day, t) if t else None
        games.append({"row": g, "day": day, "start": start,
                      "score": parse_score(format_score(g.get("Score")))})
    games.sort(key=lambda x: (x["day"], x["start"] or datetime.min))
    return games


def side_of(game, team):
    """The game as `team` saw it: opponent, home or away, goals for and against, result."""
    away, home = game["row"].get("Away", ""), game["row"].get("Home", "")
    at_home = home == team
    out = {"opponent": away if at_home else home, "home": at_home}
    if game["score"]:
        gf = game["score"]["home" if at_home else "away"]
        ga = game["score"]["away" if at_home else "home"]
        out.update(gf=gf, ga=ga, result="W" if gf > ga else "L" if gf < ga else "T")
    return out


def team_games(games, team):
    return [g for g in games if team in (g["row"].get("Away"), g["row"].get("Home"))]


# --- Sections -------------------------------------------------------------------

def streak_text(streak):
    """The GTHL's 'Won 3' as 'Won last 3', 'Tied 1' as 'Tied last game', so it
    does not read as a place in the standings."""
    parts = str(streak or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        return ""
    verb, n = parts[0].capitalize(), int(parts[1])
    return f"{verb} last game" if n == 1 else f"{verb} last {n}"


def hero(row, total):
    team = row["Team"]
    ours = team == config.TEAM_NAME
    streak = str(row.get("Streak", "")).strip()
    played = str(row.get("GP", "0")).strip() not in ("", "0")
    record = row.get("W-L-T") if played else "0-0-0"
    stats = [("PTS", row.get("PTS") or "0"), ("Win %", row.get("WIN%") if played else "–"),
             ("GP", row.get("GP") or "0")]
    stat_html = "".join(f'<div class="hero-stat"><span class="hero-stat-num">{escape(str(v))}</span>'
                        f'<span class="hero-stat-label">{k}</span></div>' for k, v in stats)
    line = f"{page_common.place_label(row)} of {total} in {page_common.division_label()}"
    if streak_text(streak):
        line += f" · {escape(streak_text(streak))}"
    return f"""
                <section class="team-hero{' is-ours' if ours else ''}">
                    <div class="team-hero-id">
                        {page_common.team_logo(team, row.get('Logo'))}
                        <div>
                            <h2 class="team-hero-name">{escape(team)}</h2>
                            <p class="team-hero-line">{line}</p>
                        </div>
                    </div>
                    <div class="team-hero-numbers">
                        <div class="team-hero-record"><span>{escape(record)}</span>
                            <span class="hero-stat-label">W-L-T</span></div>
                        {stat_html}
                    </div>
                </section>
"""


def form_chips(played, team):
    """The last five results as W / L / T chips, oldest on the left."""
    chips = ""
    for g in played[-5:]:
        s = side_of(g, team)
        word = {"W": "Win", "L": "Loss", "T": "Tie"}[s["result"]]
        lines = [f"{word} {s['gf']}\u2013{s['ga']}", f"{'vs' if s['home'] else 'at'} {s['opponent']}", f"{g['day'].strftime('%b')} {g['day'].day}"]
        chips += (f'<span class="form-chip form-{s["result"].lower()}" data-tip="{escape("||".join(lines))}" '
                  f'aria-label="{escape(", ".join(lines))}" tabindex="0" role="img">{s["result"]}</span>')
    return chips


def form(played, team):
    """The last five results, as W / L / T chips."""
    last = played[-5:]
    if not last:
        return ""
    chips = form_chips(played, team)
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Last {len(last)} game{'s' if len(last) != 1 else ''}</h3><span>Oldest to newest</span></div>
                    <div class="form-row">{chips}</div>
                </section>
"""


def division_rank(standings, team, key, best_high):
    """Where `team` ranks on a per-game figure among teams that have played."""
    values = {r["Team"]: number(r.get(key)) for r in standings
              if str(r.get("GP", "0")).strip() not in ("", "0")}
    mine = values.get(team)
    if mine is None:
        return None, None
    better = sum(1 for v in values.values() if v is not None and (v > mine if best_high else v < mine))
    return mine, better + 1


def scouting(row, standings, played, team):
    tiles = []
    gfa, off_rank = division_rank(standings, team, "GFA", True)
    gaa, def_rank = division_rank(standings, team, "GAA", False)
    if gfa is not None:
        tiles.append(("Offence", f"{gfa:.2f}", f"goals a game · {ordinal(off_rank)} in the {config.REGION}"))
    if gaa is not None:
        tiles.append(("Defence", f"{gaa:.2f}", f"against a game · {ordinal(def_rank)} in the {config.REGION}"))
    sides = [side_of(g, team) for g in played]
    if sides:
        diff = sum(s["gf"] - s["ga"] for s in sides)
        tiles.append(("Goal difference", f"{diff:+d}" if diff else "0",
                      f"{sum(s['gf'] for s in sides)} for, {sum(s['ga'] for s in sides)} against"))
    if str(row.get("GP", "0")).strip() not in ("", "0"):
        tiles.append(("Home", row.get("Home") or "0-0-0", "W-L-T"))
        tiles.append(("Away", row.get("Away") or "0-0-0", "W-L-T"))
    wins = [(s["gf"] - s["ga"], g, s) for g, s in zip(played, sides) if s["result"] == "W"]
    if wins:
        margin, g, s = max(wins, key=lambda w: (w[0], w[2]["gf"]))
        tiles.append(("Biggest win", f"{s['gf']}–{s['ga']}",
                      f"{'vs' if s['home'] else 'at'} {s['opponent']}, {g['day'].strftime('%b')} {g['day'].day}"))
    shutouts = sum(1 for s in sides if s["ga"] == 0)
    if shutouts:
        tiles.append(("Shutouts", str(shutouts), "games without conceding"))
    if not tiles:
        return ""
    cells = "".join(f'<div class="scout-tile"><span class="scout-label">{escape(k)}</span>'
                    f'<span class="scout-value">{escape(v)}</span><span class="scout-note">{escape(n)}</span></div>'
                    for k, v, n in tiles)
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Scouting report</h3></div>
                    <div class="scout-grid">{cells}</div>
                </section>
"""


def points_path(played, team):
    """Cumulative points by game against the most possible: a small line chart."""
    if len(played) < 2:
        return ""
    points, total = [0], 0
    for g in played:
        r = side_of(g, team)["result"]
        total += 2 if r == "W" else 1 if r == "T" else 0
        points.append(total)
    n, top = len(played), 2 * len(played)
    w, h = 600, 120

    def xy(i, p):
        return f"{i / n * w:.1f},{h - p / top * h:.1f}"
    line = " ".join(xy(i, p) for i, p in enumerate(points))
    # The chart is stretched to fit its box, which would turn a circle into an oval. A dot is a zero-length line with
    # round ends and a stroke that does not scale, so it stays round at any stretch.
    dots = "".join(f'<line x1="{xy(i, p).split(",")[0]}" y1="{xy(i, p).split(",")[1]}" '
                   f'x2="{xy(i, p).split(",")[0]}" y2="{xy(i, p).split(",")[1]}"/>'
                   for i, p in enumerate(points) if i)
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Points path</h3>
                        <span>{total} of a possible {top}</span></div>
                    <svg class="points-path" viewBox="-6 -6 {w + 12} {h + 12}" preserveAspectRatio="none"
                         role="img" aria-label="{total} points from {n} games, of a possible {top}">
                        <line class="pace" x1="0" y1="{h}" x2="{w}" y2="0"/>
                        <polyline class="path" points="{line}"/>
                        <g class="dots">{dots}</g>
                    </svg>
                </section>
"""


def rows_html(games, now, first=None):
    """Games as the schedule's compact rows, under a heading per month."""
    html, month = "", None
    for g in games:
        label = g["day"].strftime("%B")
        if label != month:
            if month is not None:
                html += "                    </div>\n"
            html += (f'                    <div class="week-head"><h3 class="week-label">{label}</h3></div>\n'
                     '                    <div class="week-games">\n')
            month = label
        html += game_row(g["row"], g["day"], config.TEAM_NAME.lower(), None, aware(g["start"]), now, first)
    return html + ("                    </div>\n" if html else "")


def versus_eagles(games, team, now, today):
    """The season series between this team and the Eagles."""
    us = config.TEAM_NAME
    meetings = [g for g in games if {g["row"].get("Away"), g["row"].get("Home")} == {us, team}]
    if not meetings:
        return ""
    played = [g for g in meetings if g["score"]]
    sides = [side_of(g, us) for g in played]
    w = sum(s["result"] == "W" for s in sides)
    l = sum(s["result"] == "L" for s in sides)
    t = sum(s["result"] == "T" for s in sides)
    nxt = next((g for g in meetings if not g["score"] and g["day"] >= today), None)
    note = (f"Next meeting <span data-countdown-lower{countdown_attr(nxt['day'])}>"
            f"{countdown(nxt['day'], today).lower()}</span>, {nxt['day'].strftime('%a %b')} {nxt['day'].day}"
            if nxt else "No more meetings scheduled")
    record = (f'<div class="series-record"><span class="series-num">{w}-{l}-{t}</span>'
              f'<span class="series-label">{escape(config.TEAM_NAME.split()[-1])} record</span></div>'
              if played else '<div class="series-record"><span class="series-label">Yet to meet</span></div>')
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Versus the {escape(us.split()[-1])}</h3>
                        <span>{len(meetings)} meeting{'s' if len(meetings) != 1 else ''} this season</span></div>
                    <div class="series">{record}<span class="series-next">{note}</span></div>
                    <div class="team-games">
{rows_html(meetings, now, team)}                    </div>
                </section>
"""


def eagles_series(games, standings, now, today):
    """On the Eagles' own page: their record against every opponent."""
    us = config.TEAM_NAME
    lines = ""
    for row in standings:
        team = row["Team"]
        if team == us:
            continue
        meetings = [g for g in games if {g["row"].get("Away"), g["row"].get("Home")} == {us, team}]
        sides = [side_of(g, us) for g in meetings if g["score"]]
        w = sum(s["result"] == "W" for s in sides)
        l = sum(s["result"] == "L" for s in sides)
        t = sum(s["result"] == "T" for s in sides)
        gf, ga = sum(s["gf"] for s in sides), sum(s["ga"] for s in sides)
        nxt = next((g for g in meetings if not g["score"] and g["day"] >= today), None)
        nxt_text = f"{nxt['day'].strftime('%b')} {nxt['day'].day}" if nxt else "–"
        lines += f"""                        <tr>
                            <td class="team-name"><a class="team-link" href="{page_name(team)}"><span class="team-cell">{page_common.team_logo(team, row.get('Logo'))}<span>{escape(team)}</span></span></a></td>
                            <td class="stat">{w}-{l}-{t}</td>
                            <td class="stat">{f'{gf}–{ga}' if sides else '–'}</td>
                            <td class="stat">{nxt_text}</td>
                        </tr>
"""
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Season series</h3><span>The {escape(us.split()[-1])} against everyone</span></div>
                    <div class="table-wrapper series-table">
                    <table>
                        <thead><tr><th class="team-col">Opponent</th><th class="stat">W-L-T</th>
                            <th class="stat">Goals</th><th class="stat">Next</th></tr></thead>
                        <tbody>
{lines}                        </tbody>
                    </table>
                    </div>
                </section>
"""


def next_game(upcoming, today, now):
    if not upcoming:
        return ""
    g = upcoming[0]
    rink = g["row"].get("Arena", "")
    rink_html = (directions_link(rink, "next-rink", rink) or f"<span>{escape(rink)}</span>") \
        + watch_link(g["row"], aware(g["start"]), now, css_class="game-watch next-watch")
    return next_game_card(g["row"].get("Away", ""), g["row"].get("Home", ""), g["day"],
                          g["row"].get("Time", ""), rink_html, today, href=game_page(g["row"]))


def games_section(title, games, now, note="", team=None):
    if not games:
        return ""
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>{title}</h3><span>{note}</span></div>
                    <div class="team-games">
{rows_html(games, now, team)}                    </div>
                </section>
"""


# --- Assembly -------------------------------------------------------------------

def team_page(row, standings, games, timestamp, today, now):
    team = row["Team"]
    mine = team_games(games, team)
    played = [g for g in mine if g["score"]]
    upcoming = [g for g in mine if not g["score"] and g["day"] >= today]
    ours = team == config.TEAM_NAME
    body = hero(row, len(standings))
    body += next_game(upcoming, today, now)
    body += form(played, team)
    body += scouting(row, standings, played, team)
    body += points_path(played, team)
    body += eagles_series(games, standings, now, today) if ours else versus_eagles(games, team, now, today)
    body += games_section("Results", list(reversed(played)), now, "Newest first", team)
    body += games_section("Still to play", upcoming, now, team=team)
    if not played and not upcoming:
        body += """
                <section class="team-block"><p class="team-empty">No games on the schedule yet.</p></section>
"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(team)} - {config.SITE_TITLE}</title>
{page_common.FONT_LINK}
{page_common.FAVICON_LINKS}
    <style>
{page_common.PAGE_CSS}{page_common.TEAM_CSS}    </style>
</head>
<body>
    <div class="container">
{page_common.masthead("index.html", page_common.division_label(), page_common.season_label())}

        <div class="content">
            <div class="team-page{' is-ours' if ours else ''}">
                <a class="team-back" href="index.html">&#8249; Standings</a>
{body}            </div>
{page_common.freshness(timestamp)}        </div>

{page_common.page_end()}    </div>
{page_common.SCHEDULE_JS}</body>
</html>
"""


def generate(today=None):
    try:
        with open("standings.json", encoding="utf-8") as f:
            standings_data = json.load(f)
        with open("schedule.json", encoding="utf-8") as f:
            schedule = json.load(f).get("schedule", [])
    except FileNotFoundError as exc:
        print(f"Team pages skipped: {exc.filename} not found")
        return []
    standings = page_common.rank_standings(standings_data.get("standings", []))
    now = datetime.now(page_common.TORONTO)
    today = today or now.date()
    games = all_games(schedule)
    written = []
    for row in standings:
        name = page_name(row["Team"])
        with open(name, "w", encoding="utf-8") as f:
            f.write(team_page(row, standings, games, standings_data.get("timestamp", ""), today, now))
        written.append(name)
    # A team that has left the division takes its page with it.
    for stale in set(glob.glob("team-*.html")) - set(written):
        os.remove(stale)
    print(f"Generated {len(written)} team pages")
    return written


if __name__ == "__main__":
    generate()

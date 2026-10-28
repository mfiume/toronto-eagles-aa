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
  game sheet: for our games, the league's official score by period and the goals, penalties and timeouts,
              and the shots a parent tracked, when there are any (game_shots.json)
  tale of the tape: the two teams side by side, the better figure in bold
  season series: every meeting of the two this season, each linking on
"""

import glob
import json
import os
from datetime import datetime
from html import escape

import arenas
import config
import page_common
from generate_schedule_html import (countdown_attr, aware, countdown, game_page, game_row, live_flag, load_film, maps_link,
                                    stream_state, team_name_html, watch_button)
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
    return (f'<span class="match-status upcoming"{countdown_attr(g["day"])}>'
            f'{escape(countdown(g["day"], today))}</span>')


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


def actions(g, now, film=False):
    row = g["row"]
    buttons = ""
    start = aware(g["start"])
    if start is not None:
        buttons += watch_button(row.get("Stream"), start, now)
    rink = row.get("Arena", "")
    google = arenas.directions_url(rink)
    if google and not g["score"]:
        buttons += maps_link(google, arenas.apple_directions_url(rink), "match-btn", "Directions",
                             f"Directions to {rink}")
    return f'\n                <div class="match-actions">{buttons}</div>\n' if buttons or film else ""


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


# --- The league's game sheet --------------------------------------------------------

SHEETS_FILE = "game_sheets.json"
# The league's penalty codes in words: the Ontario Hockey Federation's list of minor and major penalty abbreviations, and the
# Hockey Canada rule number the league sometimes writes in place of one (8.6 is tripping). A code not here is shown as written.
PENALTIES = {
    "AGG": "Aggressor", "BC": "Body checking", "BDG": "Boarding", "BM": "Bench minor", "BRS": "Broken stick",
    "BUTT": "Butt ending", "CC": "Cross checking", "CFB": "Checking from behind", "CHG": "Charging",
    "DE": "Dangerous equipment", "DG": "Delay of game", "ELB": "Elbowing", "FI": "Fighting", "FMSK": "Face masking",
    "FOP": "Falling on the puck", "GLC": "Goalie leaving crease", "HB": "Head butting", "HC": "Head contact",
    "HKG": "Hooking", "HO": "Holding", "HP": "Handling the puck", "HS": "High sticking", "IE": "Illegal equipment",
    "IP": "Ineligible player", "INS": "Instigator", "INT": "Interference", "INTGT": "Interference with the goalie",
    "KNE": "Kneeing", "LPB": "Leaving the penalty bench", "RAW": "Roughing after the whistle", "RH": "Removing helmet",
    "RO": "Roughing", "SL": "Slashing", "SP": "Spearing", "TMP": "Too many players", "TR": "Tripping",
    "TS": "Throwing the stick", "USC": "Unsportsmanlike conduct",
}


def penalty_name(code):
    code = (code or "").strip()
    if code.startswith("8.6"):
        return "Tripping"
    return PENALTIES.get(code.upper(), code)


SHOTS_FILE = "game_shots.json"


def load_shots():
    """Shots on goal a parent tracked for a game, by hand: {game id: {"eagles": n, "opponent": n}}. Optional, and never in the league's sheet."""
    try:
        with open(SHOTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def compare_block(title, ours, theirs, ours_name, their_name):
    """One comparison: each team's number either side of the title, over a bar split in proportion, ours in red."""
    total = max(ours + theirs, 1)
    return (f'<div class="compare"><div class="compare-head"><span class="compare-n us">{ours}</span>'
            f'<span class="compare-title">{title}</span>'
            f'<span class="compare-n">{theirs}</span></div>'
            f'<div class="compare-bar" role="img" aria-label="{title}: {escape(ours_name)} {ours}, {escape(their_name)} {theirs}">'
            f'<i class="us" style="flex:{ours / total:.4f}"></i><i style="flex:{theirs / total:.4f}"></i></div></div>')


def comparisons(sheet, shots):
    """Goals and penalties from the sheet, and shots when someone tracked them, for our games."""
    if config.TEAM_NAME not in (sheet["home"], sheet["away"]):
        return ""
    us = "home" if sheet["home"] == config.TEAM_NAME else "away"
    them = "away" if us == "home" else "home"
    names = (sheet[us], sheet[them])
    count = lambda items, side: sum(1 for i in items if i["side"] == side)
    blocks = [compare_block("Goals", sheet["final"][us], sheet["final"][them], *names)]
    if shots:
        blocks.append(compare_block("Shots", shots["eagles"], shots["opponent"], *names))
    if sheet["penalties"]:
        blocks.append(compare_block("Penalties", count(sheet["penalties"], us), count(sheet["penalties"], them), *names))
    return f'<div class="compare-row">{"".join(blocks)}</div>'


def load_sheets():
    try:
        with open(SHEETS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def clock_seconds(clock):
    m, sec = clock.split(":")
    return int(m) * 60 + int(sec)


def period_label(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, "OT" if n == 4 else f"P{n}")


def clock_left(seconds):
    return f"{seconds // 60}:{seconds % 60:02d}"


def sheet_timeline(sheet):
    """
    The game's moments laid out by period, one line for each, running left to right from the opening faceoff. A goal is a
    dot on the line, a timeout a diamond, and a penalty a bar as long as the penalty, hung just under the line. Penalties
    that run at the same time (matching minors, a power play) stack one under the other instead of covering each other.
    Ours are red and theirs dark. The sheet gives each moment by the time left on the clock, so a moment at 3:15 left sits
    8:45 of a 12 minute period in.
    """
    length = 12 * 60
    ours = "home" if sheet["home"] == config.TEAM_NAME else "away" if sheet["away"] == config.TEAM_NAME else None
    name = {"home": sheet["home"], "away": sheet["away"]}
    theirs = name["away" if ours == "home" else "home"] if ours else None

    def secs(clock):
        m, sec = clock.split(":")
        return int(m) * 60 + int(sec)

    def pos(clock):
        return max(0.0, min(100.0, (1 - secs(clock) / length) * 100))

    def mine(side):
        return "us" if side == ours else "them"

    # running score, to say what each goal made it
    score = {"home": 0, "away": 0}
    running = {}
    for g in sorted(sheet["goals"], key=lambda g: (g["period"], -secs(g["clock"]))):
        score[g["side"]] += 1
        running[(g["period"], g["clock"], g["side"])] = (score["away"], score["home"])

    # "Toronto Eagles" is "Eagles" in a tooltip: the score line is short enough to read at a glance
    nick = {side: name[side].split()[-1] for side in ("home", "away")}

    def tip(*lines, side=None):
        """What the tooltip says, one line each, as an attribute the page's script reads. The same words label the mark for a screen reader.
        With a side, the heading carries that team's logo."""
        text = "||".join(lines)
        src = page_common.logo_src(name[side]) if side else None
        logo = f' data-tip-logo="{escape(src)}"' if src else ""
        return f'data-tip="{escape(text)}"{logo} aria-label="{escape(" - ".join(lines))}" tabindex="0" role="img"'

    def moment(kind, n, clock):
        """Which moment of the game a mark is, so the film can be matched to it once a signed-in viewer opens it. The league's own sheet already says this publicly."""
        return f'data-m="{kind}|{n}|{clock}"'

    def when(n, clock):
        return f'{period_label(n)} period, {clock} left'

    def score_at(n, clock):
        """The score just before a moment: the goals scored earlier in the game, so a goal at the same second is not counted."""
        a = sum(1 for g in sheet["goals"] if g["side"] == "away" and (g["period"], -secs(g["clock"])) < (n, -secs(clock)))
        h = sum(1 for g in sheet["goals"] if g["side"] == "home" and (g["period"], -secs(g["clock"])) < (n, -secs(clock)))
        return "Score: " + nick["away"] + " " + str(a) + ", " + nick["home"] + " " + str(h)

    blocks = ""
    for p in sheet["periods"]:
        n = p["period"]
        marks = ""
        for g in sheet["goals"]:
            if g["period"] == n:
                a, h = running[(n, g["clock"], g["side"])]
                kind = f' ({g["kind"]})' if g.get("kind") else ""
                head = "Goal, " + name[g["side"]] + kind
                after = "Score: " + nick["away"] + " " + str(a) + ", " + nick["home"] + " " + str(h)
                marks += (f'<span class="tl-dot {mine(g["side"])}" style="left:{pos(g["clock"]):.2f}%" '
                          f'{tip(head, when(n, g["clock"]), after, side=g["side"])} {moment("goal", n, g["clock"])}></span>')
        for t in sheet["timeouts"]:
            if t["period"] == n:
                head = "Timeout, " + name[t["side"]]
                marks += (f'<span class="tl-to {mine(t["side"])}" style="left:{pos(t["clock"]):.2f}%" '
                          f'{tip(head, when(n, t["clock"]), score_at(n, t["clock"]), side=t["side"])} {moment("timeout", n, t["clock"])}></span>')
        # penalties, each in the first row under the line where it does not run into one already there
        rows = []
        bars = ""
        for t in sorted((t for t in sheet["penalties"] if t["period"] == n), key=lambda t: pos(t["clock"])):
            start = pos(t["clock"])
            end = min(start + t["minutes"] * 60 / length * 100, 100)
            row = next((r for r, last in enumerate(rows) if last <= start), len(rows))
            if row == len(rows):
                rows.append(end)
            else:
                rows[row] = end
            what = penalty_name(t["code"]) or "Penalty"
            head = "Penalty, " + name[t["side"]]
            detail = what + ", " + str(t["minutes"]) + " min"
            bars += (f'<span class="tl-pen {mine(t["side"])}" style="left:{start:.2f}%;width:{end - start:.2f}%;top:{19 + row * 7}px" '
                     f'{tip(head, detail, when(n, t["clock"]), score_at(n, t["clock"]), side=t["side"])} {moment("penalty", n, t["clock"])}></span>')
        height = 19 + max(len(rows), 1) * 7 + 2 if rows else 21
        grid = "".join(f'<span class="tl-tick" style="left:{k * 25}%"></span>' for k in range(1, 4))
        blocks += (f'<div class="tl-period"><div class="tl-name">{period_label(n)}</div>'
                   f'<div class="tl-track" style="height:{height}px">{grid}<div class="tl-line"></div>{bars}{marks}</div></div>')
    axis = ('<div class="tl-period tl-axis"><div class="tl-name"></div><div class="tl-track">'
            + "".join(f'<span class="tl-label" style="left:{k * 25}%">{c}</span>' for k, c in enumerate(("12:00", "9:00", "6:00", "3:00")))
            + '<span class="tl-label end">0:00</span></div></div>')
    who = (f'<span class="tl-key"><i class="tl-dot us"></i>{escape(config.TEAM_NAME)}</span>'
           f'<span class="tl-key"><i class="tl-dot them"></i>{escape(theirs)}</span>') if ours else ""
    legend = (f'<div class="tl-legend">{who}<span><i class="tl-dot"></i>Goal</span><span><i class="tl-pen"></i>Penalty, as long as it lasts</span>'
              f'<span><i class="tl-to"></i>Timeout</span></div>')
    return f'<div class="tl">{axis}{blocks}{legend}</div>'


def game_sheet(sheet, shots=None):
    """
    The league's official sheet for the game: the score by period, then the goals, penalties and timeouts in the order
    they happened. No player is named and no jersey number is shown: the sheet is published without them.
    """
    if not sheet:
        return ""
    name = {"home": escape(sheet["home"]), "away": escape(sheet["away"])}
    head = "".join(f"<th>{period_label(p['period'])}</th>" for p in sheet["periods"])
    rows = "".join(
        f'<tr><td class="sheet-team">{name[side]}</td>'
        + "".join(f"<td>{p[side]}</td>" for p in sheet["periods"])
        + f'<td class="sheet-total">{sheet["final"][side]}</td></tr>'
        for side in ("away", "home"))
    table = (f'<div class="table-wrapper"><table class="sheet-score"><thead><tr><th class="sheet-team"></th>{head}'
             f'<th>Final</th></tr></thead><tbody>{rows}</tbody></table></div>')

    def listing(title, items, line, kind):
        if not items:
            return ""
        lis = "".join(f'<li data-m="{kind}|{i["period"]}|{i["clock"]}"><span class="sheet-when">{period_label(i["period"])} · {i["clock"]}</span>{line(i)}</li>' for i in items)
        return f'<div class="sheet-list"><h4>{title}</h4><ul>{lis}</ul></div>'

    def who(side, text, note="", score=""):
        """The team's logo with what happened beside it; the team's name is in the tooltip and read out for a screen reader."""
        team = sheet[side]
        extra = f' <span class="sheet-note">{escape(note)}</span>' if note else ""
        return (f'<span class="sheet-what" data-tip="{escape(team)}" aria-label="{escape(team)}: {escape(text)}" tabindex="0">'
                f'{page_common.team_logo(team)}<span>{escape(text)}</span>{extra}'
                + (f'<span class="sheet-score-now">{score}</span>' if score else "") + '</span>')

    # The score after each goal, ours first, counted in the order the goals were scored.
    mine = "home" if sheet["home"] == config.TEAM_NAME else "away"
    running, after = {"home": 0, "away": 0}, {}
    for g in sorted(sheet["goals"], key=lambda g: (g["period"], -clock_seconds(g["clock"]))):
        running[g["side"]] += 1
        after[id(g)] = f'{running[mine]}\u2013{running["home" if mine == "away" else "away"]}'

    def goal(g):
        return who(g["side"], "Goal", g.get("kind") or "", after[id(g)])

    def penalty(p):
        return who(p["side"], penalty_name(p["code"]) or "Penalty", f'{p["minutes"]} min')

    def timeout(t):
        return who(t["side"], "Timeout")

    lists = (listing("Scoring", sheet["goals"], goal, "goal") + listing("Penalties", sheet["penalties"], penalty, "penalty")
             + listing("Timeouts", sheet["timeouts"], timeout, "timeout"))
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Game sheet</h3><span>Official, from the league</span></div>
                    <div class="sheet-card">
                        {table}
                        {comparisons(sheet, shots)}
                        {sheet_timeline(sheet)}
                        <div class="sheet-lists">{lists}</div>
                    </div>
                </section>
"""


# --- Assembly -------------------------------------------------------------------

def page(g, standings, games, timestamp, today, now, sheets=None, shot_counts=None, film=None):
    sheets = sheets or {}
    shot_counts = shot_counts or {}
    row = g["row"]
    title = f"{row.get('Away', '')} at {row.get('Home', '')}"
    body = matchup(g, standings, today, now)
    body += actions(g, now, film=bool(film))
    body += where_when(g)
    gid = game_page(row)[len("game-"):-len(".html")]
    body += game_sheet(sheets.get(gid), shot_counts.get(gid))
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
{film_payload(film)}{page_common.SCHEDULE_JS}</body>
</html>
"""


def film_payload(sealed):
    """The film button, sealed with the team password, and the script that opens it for a signed-in phone. Nothing for a game with no film."""
    if not sealed:
        return ""
    data = json.dumps(sealed).replace("</", "<\\/")
    return f'    <script type="application/json" id="game-film">{data}</script>\n{page_common.FILM_JS}'


# The video player's script. It is sealed with the film, never written into the public page, so the page names no video host
# and nothing is fetched from it until a signed-in viewer opens the review.
PLAYER_API = "https://www.youtube.com/iframe_api"


def film_package(entry):
    """
    What is sealed for a game with a film: the button, the address, and the moments of the game sheet that are placed on the film
    (kind, period, clock, and the second of the video), and the address of the video player's script. The script puts the button in place and turns the matching marks and rows
    into links to the video at that second. Like the button, none of it is in the page unless it is sealed.
    """
    return json.dumps({"html": film_button(entry["url"]), "url": entry["url"], "moments": entry["moments"], "api": PLAYER_API},
                      separators=(",", ":"))


def film_button(url):
    return (f'<a class="match-btn film" href="{escape(url)}" target="_blank" rel="noopener noreferrer">'
            f'{page_common.FILM_ICON}<span>Watch on YouTube</span></a>')


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
    sheets = load_sheets()
    films = load_film()
    password = os.environ.get("TEAM_EVENTS_PASSWORD", "")
    sealer = None
    if films and password:
        import team_crypto
        sealer = team_crypto.Sealer(password)
    written = {}
    for g in games:
        name = game_page(g["row"])
        gid = name[len("game-"):-len(".html")]
        with open(name, "w", encoding="utf-8") as f:
            f.write(page(g, standings, games, schedule_data.get("timestamp", ""), today, now, sheets, load_shots(),
                               film=sealer.seal(film_package(films[gid])) if sealer and films.get(gid) else None))
        written[name] = True
    # A game the GTHL no longer lists takes its page with it.
    for stale in set(glob.glob("game-*.html")) - set(written):
        os.remove(stale)
    print(f"Generated {len(written)} game pages")
    return list(written)


if __name__ == "__main__":
    generate()

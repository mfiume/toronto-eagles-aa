#!/usr/bin/env python3
"""
Generate HTML page from scraped schedule data

The page is built twice. The public version has the GTHL's league games only.
When the team calendar is available (team_events.json, from teamsnap.py) and a
team password is set (TEAM_EVENTS_PASSWORD), a second version adds the team's
own events: practices, dryland, tournaments and the games the GTHL does not
list, plus arrival times and jersey colours on our league games. That version
is encrypted with the password and embedded in the page, which swaps it in once
a parent unlocks it. Nothing about team events is written in the clear.
"""

import json
import os
import re
from datetime import datetime, timedelta
from html import escape

import arenas
import config
import page_common
from season_schedule import parse_score

TEAM_EVENTS_FILE = "team_events.json"
PASSWORD_ENV = "TEAM_EVENTS_PASSWORD"


def parse_game_date(raw):
    """'12-Oct-2026 Mon' -> date(2026, 10, 12), or None if unreadable."""
    try:
        return datetime.strptime(raw.split()[0], "%d-%b-%Y").date()
    except (ValueError, IndexError, AttributeError):
        return None


def parse_game_time(raw):
    """'7:10 PM' -> time(19, 10), or None."""
    try:
        return datetime.strptime((raw or "").strip().upper(), "%I:%M %p").time()
    except ValueError:
        return None


def format_score(raw):
    """
    The score, or nothing at all if the game has not been played.

    The GTHL writes an unplayed game's score as a bare ':' separator, which
    reads as a broken cell rather than as "no result yet".
    """
    cleaned = (raw or "").strip()
    return "" if cleaned in ("", ":") else cleaned


def countdown(day, today):
    """How far off a game is, from today in Toronto."""
    days = (day - today).days
    if days == 0:
        return "Today"
    if days == 1:
        return "Tomorrow"
    return f"In {days} days"


def week_label(monday, this_monday):
    """'This week', 'Next week', 'Last week', or 'Week of Oct 19'."""
    weeks = (monday - this_monday).days // 7
    if weeks == 0:
        return "This week"
    if weeks == 1:
        return "Next week"
    if weeks == -1:
        return "Last week"
    return f"Week of {monday.strftime('%b')} {monday.day}"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def clock(t):
    """time(19, 10) -> '7:10 PM'."""
    return t.strftime("%I:%M %p").lstrip("0")


def maps_link(google, apple, css_class, text, label):
    """A directions link: Google Maps in the HTML, Apple Maps swapped in on iOS."""
    apple_attr = f' data-apple-maps="{escape(apple)}"' if apple else ''
    return (f'<a class="{css_class}" href="{escape(google)}"{apple_attr} '
            f'target="_blank" rel="noopener noreferrer" aria-label="{escape(label)}">'
            f'{escape(text)}</a>')


def directions_link(rink, css_class, text):
    """A directions link for a GTHL rink, or nothing if its address is not known."""
    url = arenas.directions_url(rink)
    if not url:
        return ""
    arena = arenas.find(rink)
    return maps_link(url, arenas.apple_directions_url(rink), css_class, text,
                     f"Directions to {arena['name']}, {arenas.address(arena)}")


def rink_cell(rink):
    """The rink, as a directions link when its address is known."""
    linked = directions_link(rink, "game-rink", rink)
    return linked or f'<div class="game-rink">{escape(rink)}</div>'


def venue_cell(venue, address, css_class="game-rink"):
    """A TeamSnap venue, linked to directions to TeamSnap's own address."""
    text = short_venue(venue) or (address or "")
    google, apple = arenas.address_urls(address)
    if google and text:
        return maps_link(google, apple, css_class, text, f"Directions to {text}, {address}")
    return f'<div class="{css_class}">{escape(text)}</div>' if text else ''


def short_venue(venue):
    """'Ford Performance Center - Rink 1' -> 'Ford Performance Center · Rink 1'."""
    return re.sub(r"\s+-\s+", " · ", venue.strip()) if venue else ""


def wear_text(wear, game):
    """'white' -> 'White jersey' for a game; dress codes pass through."""
    if not wear:
        return ""
    wear = wear.strip()
    wear = wear[0].upper() + wear[1:]
    if game and not re.search(r"jersey|clothes|socks", wear, re.I):
        wear += " jersey"
    return wear


def extra_line(*parts, details=False):
    """
    A small line under a row. With details=True it is the row's tap-to-reveal
    detail (arrival time, what to wear), hidden until the row is opened.
    """
    parts = [p for p in parts if p]
    if not parts:
        return ""
    cls = "game-extra game-details" if details else "game-extra"
    return f'<div class="{cls}">' + " · ".join(escape(p) for p in parts) + "</div>"


def row_attrs(classes, details):
    """
    The opening tag's attributes for a row. A row with details can be opened:
    it is focusable, announces itself as a toggle, and shows a chevron.
    """
    if not details:
        return f'class="{classes}"'
    return f'class="{classes} has-details" tabindex="0" role="button" aria-expanded="false"'


CHEVRON = '<span class="game-chevron" aria-hidden="true"></span>'



def arrival(event):
    return f"Arrive {event['arrive']}" if event and event.get("arrive") else ""


# --- Rows ---------------------------------------------------------------------

def game_row(game, day, our_team, team=None):
    """
    One league game as a compact row: day and time, both teams stacked, the
    rink. Ours look the same as everyone else's apart from the red bar.

    Once played, "Final" takes the time's place and each team's goals sit at
    the end of its own line, the winner in bold, so a score never reads as a
    time. Our games add a W, L or T. A played game drops the rink: nobody needs
    directions to it any more, and the names get the room. The GTHL writes the
    score as away:home, the order of its own columns.

    `team` is the matching TeamSnap entry, if any, which adds arrival time and
    jersey colour in the team version of the page.
    """
    away, home = game.get('Away', ''), game.get('Home', '')
    ours = our_team in (away.lower(), home.lower())
    score = parse_score(format_score(game.get('Score')))
    day_text = f"{day.strftime('%a')} {day.day}" if day else escape(game.get('Date', ''))

    def team_line(name, goals, other):
        classes = ['game-team']
        if name.lower() == our_team:
            classes.append('us')
        if score is not None:
            classes.append('won' if goals > other else 'lost' if goals < other else 'tied')
        goals_html = f'<span class="game-goals">{goals}</span>' if score is not None else ''
        return (f'<div class="{" ".join(classes)}">{page_common.team_logo(name)}'
                f'<span class="game-name">{escape(name)}</span>{goals_html}</div>')

    if score is not None:
        a, h = score['away'], score['home']
        status = '<span class="game-final">Final</span>'
        if ours:
            mine, theirs = (h, a) if home.lower() == our_team else (a, h)
            result = 'W' if mine > theirs else 'L' if mine < theirs else 'T'
            status += (f'<span class="game-result result-{result.lower()}" '
                       f'title="{ {"W": "Win", "L": "Loss", "T": "Tie"}[result] }">{result}</span>')
        when = f'<span class="game-time">{status}</span>'
        teams = team_line(away, a, h) + team_line(home, h, a)
        extra = ''
    else:
        when = f'<span class="game-time">{escape(game.get("Time", ""))}</span>'
        teams = team_line(away, 0, 0) + team_line(home, 0, 0)
        extra = extra_line(arrival(team), wear_text(team.get("wear"), True) if team else "",
                           details=True)

    classes = f"game{' is-ours' if ours else ''}{' is-final' if score else ''}"
    return f"""                    <div {row_attrs(classes, extra)}>
                        <div class="game-when"><span class="game-day">{day_text}</span>
                            {when}{CHEVRON if extra else ''}</div>
                        <div class="game-teams">{teams}{extra}</div>
                        {'' if score else rink_cell(game.get('Arena', ''))}
                    </div>
"""


def team_game_row(event, start):
    """A game only TeamSnap lists: exhibition, preseason or tournament."""
    us, them = config.TEAM_NAME, event["opponent"]
    away, home = (them, us) if event["home"] else (us, them)

    def team_line(name):
        cls = 'game-team us' if name == us else 'game-team'
        return (f'<div class="{cls}">{page_common.team_logo(name)}'
                f'<span class="game-name">{escape(name)}</span></div>')

    time_text = clock(start.time()) if event.get("timed") else "Time TBA"
    details = extra_line(arrival(event), wear_text(event.get("wear"), True), details=True)
    return f"""                    <div {row_attrs("game is-ours team-game", details)}>
                        <div class="game-when"><span class="game-day">{start.strftime('%a')} {start.day}</span>
                            <span class="game-time">{time_text}</span>{CHEVRON if details else ''}</div>
                        <div class="game-teams">{team_line(away)}{team_line(home)}{extra_line(event.get("label"))}{details}</div>
                        {venue_cell(event.get("venue"), event.get("address"))}
                    </div>
"""


EVENT_TITLES = {"practice": "Practice", "dryland": "Dryland"}


def team_event_row(event, start):
    """A practice, dryland session, tournament or other team event."""
    kind = event["kind"]
    title = EVENT_TITLES.get(kind) or event["title"]
    time_text = clock(start.time()) if event.get("timed") else "All day"
    tag = '<span class="event-tag">Tournament</span>' if kind == "tournament" else ''
    wear = wear_text(event.get("wear"), False) if kind != "practice" else ""
    details = extra_line(arrival(event) if event.get("timed") else "", wear, details=True)
    return f"""                    <div {row_attrs(f"game is-ours team-event kind-{kind}", details)}>
                        <div class="game-when"><span class="game-day">{start.strftime('%a')} {start.day}</span>
                            <span class="game-time">{time_text}</span>{CHEVRON if details else ''}</div>
                        <div class="game-teams"><div class="event-title">{tag}<span>{escape(title)}</span></div>{details}</div>
                        {venue_cell(event.get("venue"), event.get("address"))}
                    </div>
"""


# --- Cards ----------------------------------------------------------------------

def next_game_card(away, home, day, time_text, rink_html, today, extra=""):
    """The card for the next Eagles game: both teams, when and where."""
    return f"""
                <section class="next" aria-label="Next game">
                    <div class="next-top"><span>Next game</span>
                        <span class="next-when">{countdown(day, today)}</span></div>
                    <div class="face">
                        <div class="face-team">{page_common.team_logo(away)}
                            <span>{escape(away)}<span class="face-role">Away</span></span></div>
                        <div class="face-vs">VS</div>
                        <div class="face-team home">{page_common.team_logo(home)}
                            <span>{escape(home)}<span class="face-role">Home</span></span></div>
                    </div>
                    <div class="next-foot">
                        <span><strong>{day.strftime('%A, %B')} {day.day}</strong></span>
                        <span><strong>{escape(time_text)}</strong></span>
                        {rink_html}
                    </div>{extra}
                </section>
"""


LOGIN_DIALOG = """
            <dialog class="login-dialog" id="login-dialog" aria-labelledby="login-title">
                <form method="dialog">
                    <h2 id="login-title">Team Login</h2>
                    <p>Enter the team password to see practices, dryland and team events.</p>
                    <label for="login-password">Team password</label>
                    <input id="login-password" class="login-input" type="password"
                           autocomplete="current-password" required>
                    <p class="login-msg" role="status" aria-live="polite"></p>
                    <div class="login-actions">
                        <button type="button" class="login-btn secondary" data-login-cancel>Cancel</button>
                        <button type="submit" class="login-btn">Log in</button>
                    </div>
                </form>
            </dialog>
"""


# --- Assembly -------------------------------------------------------------------

def match_team_games(league, team_events, our_team):
    """
    Pair each of our league games with its TeamSnap entry: same day, start
    within 45 minutes. Returns {league index: event} and the uids it used, so
    a matched TeamSnap game is not listed a second time.
    """
    matches, used = {}, set()
    team_games = [e for e in team_events if e["kind"] == "game"]
    for i, (game, day, start) in enumerate(league):
        if not (day and start) or our_team not in (game.get('Away', '').lower(), game.get('Home', '').lower()):
            continue
        for e in team_games:
            if e["uid"] in used:
                continue
            e_start = datetime.fromisoformat(e["start"])
            if e_start.date() == day and abs((e_start - start).total_seconds()) <= 45 * 60:
                matches[i] = e
                used.add(e["uid"])
                break
    return matches, used


def build_block(schedule, today, our_team, team_events=None):
    """
    The schedule itself: next-game card, heading with the filter, and the
    weeks. Without team_events this is the public version.
    """
    this_monday = today - timedelta(days=today.weekday())

    def is_ours(game):
        return our_team in (game.get('Away', '').lower(), game.get('Home', '').lower())

    league = []
    for g in schedule:
        day = parse_game_date(g.get('Date', ''))
        t = parse_game_time(g.get('Time', ''))
        league.append((g, day, datetime.combine(day, t) if day and t else None))

    matches, used = match_team_games(league, team_events or [], our_team)

    # Everything that goes in the weeks, as (sort key, day, html, ours, kind).
    items = []
    for i, (g, day, start) in enumerate(league):
        key = start or (datetime.combine(day, datetime.min.time()) if day else datetime.max)
        items.append((key, day, game_row(g, day, our_team, matches.get(i)), is_ours(g), "game"))

    first_day = min((d for _, d, _ in league if d), default=today)
    last_day = max((d for _, d, _ in league if d), default=today)
    window_start = min(first_day, today)
    window_end = max(last_day, today + timedelta(days=config.SCHEDULE_DAYS_AHEAD))
    for e in team_events or []:
        if e["uid"] in used:
            continue
        start = datetime.fromisoformat(e["start"])
        if not (window_start <= start.date() <= window_end):
            continue
        if e["kind"] == "game":
            items.append((start, start.date(), team_game_row(e, start), True, "game"))
        else:
            items.append((start, start.date(), team_event_row(e, start), True, "event"))
    items.sort(key=lambda it: it[0])

    # The next game, from the league schedule or, unlocked, any of ours.
    candidates = []
    for i, (g, day, start) in enumerate(league):
        if is_ours(g) and day and day >= today and not format_score(g.get('Score')):
            team = matches.get(i)
            rink = g.get('Arena', '')
            rink_html = directions_link(rink, 'next-rink', rink) or f"<span>{escape(rink)}</span>"
            extra = extra_line(arrival(team), wear_text(team.get("wear"), True) if team else "")
            candidates.append((start or datetime.combine(day, datetime.min.time()),
                               (g.get('Away', ''), g.get('Home', ''), day, g.get('Time', ''), rink_html, today,
                                f'\n                    <div class="next-extra">{extra}</div>' if extra else '')))
    for e in team_events or []:
        start = datetime.fromisoformat(e["start"])
        if e["kind"] == "game" and e["uid"] not in used and start.date() >= today:
            us, them = config.TEAM_NAME, e["opponent"]
            away, home = (them, us) if e["home"] else (us, them)
            extra = extra_line(e.get("label"), arrival(e), wear_text(e.get("wear"), True))
            rink_html = venue_cell(e.get("venue"), e.get("address"), "next-rink")
            candidates.append((start, (away, home, start.date(),
                                       clock(start.time()) if e.get("timed") else "Time TBA",
                                       rink_html, today,
                                       f'\n                    <div class="next-extra">{extra}</div>' if extra else '')))
    html = ''
    if candidates:
        html += next_game_card(*min(candidates, key=lambda c: c[0])[1])

    games_ours = sum(1 for it in items if it[3] and it[4] == "game")
    games_all = sum(1 for it in items if it[4] == "game")
    default_ours = games_ours > 0
    short_name = config.TEAM_NAME.split()[-1]
    html += f"""
                <div class="sched-head">
                    <h2>Schedule</h2>
                    <div class="sched-filter" role="group" aria-label="Which games to show">
                        <button type="button" class="sched-filter-btn" data-filter="ours"
                                aria-pressed="{str(default_ours).lower()}">{short_name}
                            <span class="sched-filter-count">{games_ours}</span></button>
                        <button type="button" class="sched-filter-btn" data-filter="all"
                                aria-pressed="{str(not default_ours).lower()}">All
                            <span class="sched-filter-count">{games_all}</span></button>
                    </div>
                </div>
"""

    html += f"""
                <div class="sched-weeks{' filter-ours' if default_ours else ''}"
                     data-schedule-view data-has-ours="{int(bool(games_ours))}">
"""
    weeks = []
    for it in items:
        day = it[1]
        monday = day - timedelta(days=day.weekday()) if day else None
        if weeks and monday is not None and weeks[-1][0] == monday:
            weeks[-1][1].append(it)
        else:
            weeks.append((monday, [it]))

    for monday, week in weeks:
        g_ours = sum(1 for it in week if it[3] and it[4] == "game")
        g_all = sum(1 for it in week if it[4] == "game")
        n_events = sum(1 for it in week if it[4] == "event")
        events_note = f" · {plural(n_events, 'team event')}" if n_events else ""
        label = week_label(monday, this_monday) if monday else "Date to be confirmed"
        now = ' now' if monday == this_monday else ''
        has_ours = any(it[3] for it in week)
        html += f"""                <section class="week" data-ours="{int(has_ours)}">
                    <div class="week-head"><h3 class="week-label{now}">{label}</h3>
                        <span class="week-count"><span class="count-ours">{plural(g_ours, 'game')}{events_note}</span><span
                            class="count-all">{plural(g_all, 'game')}{events_note}</span></span></div>
                    <div class="week-games">
"""
        for it in week:
            html += it[2]
        html += "                    </div>\n                </section>\n"

    html += "                </div>\n"
    return html



def load_team_events():
    """The team calendar and password, or (None, None) if either is missing."""
    password = os.environ.get(PASSWORD_ENV, "")
    if not password or not os.path.exists(TEAM_EVENTS_FILE):
        return None, None
    with open(TEAM_EVENTS_FILE, encoding="utf-8") as f:
        return json.load(f).get("events", []), password


def generate_html(today=None):
    """Generate HTML page from schedule.json"""

    # Load schedule data
    with open('schedule.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    schedule = data.get('schedule', [])
    timestamp = data.get('timestamp', '')
    filters = data.get('filters', {})
    error = data.get('error')

    our_team = config.TEAM_NAME.lower()
    # Week labels and the countdown are relative to the day the page is built.
    # The workflow rebuilds it hourly, so "This week" turns over on Monday.
    today = today or datetime.now(page_common.TORONTO).date()

    team_events, password = load_team_events()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.SITE_TITLE} - Schedule</title>
{page_common.FONT_LINK}
{page_common.FAVICON_LINKS}
    <style>
{page_common.PAGE_CSS}    </style>
{page_common.SCHEDULE_NOSCRIPT}</head>
<body>
    <div class="container">
{page_common.masthead("schedule.html", page_common.division_label(), page_common.season_label())}

        <div class="content">
"""

    if error:
        html += f"""
            <div class="error">
                <h2>Error Loading Schedule</h2>
                <p>{error}</p>
                <p>The scraper will try again during the next scheduled run.</p>
            </div>
{page_common.freshness(timestamp)}"""
    elif not schedule:
        html += f"""
            <div class="notice">
                <h2>No games scheduled</h2>
                <p>The GTHL has not posted any {config.DIVISION} {config.CATEGORY}
                games between {filters.get('from_date', '')} and
                {filters.get('to_date', '')}.</p>
            </div>
{page_common.freshness(timestamp)}"""
    else:
        html += '            <div class="schedule" data-schedule-block>\n'
        html += build_block(schedule, today, our_team)
        html += f"""            </div>
{page_common.freshness(timestamp)}"""
        if team_events is not None:
            import team_crypto
            sealed = team_crypto.encrypt(build_block(schedule, today, our_team, team_events), password)
            # A JSON script block is inert data; "</" is escaped so the
            # ciphertext can never close the tag.
            payload = json.dumps(sealed).replace("</", "<\\/")
            html += f'            <script type="application/json" id="team-events">{payload}</script>\n'
            html += LOGIN_DIALOG

    html += f"""        </div>

{page_common.page_end()}    </div>
{page_common.SCHEDULE_JS}</body>
</html>
"""

    # Write to file
    with open('schedule.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("Generated schedule.html" + (" with encrypted team events" if team_events is not None else ""))


if __name__ == '__main__':
    generate_html()

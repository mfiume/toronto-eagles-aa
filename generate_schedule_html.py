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
import season_schedule
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


# How a week's team events are counted in its heading, in this order. Dryland
# reads as a mass noun ("2 dryland"), so it is never pluralised.
EVENT_COUNTS = [
    ("practice", lambda n: plural(n, "practice")),
    ("dryland", lambda n: f"{n} dryland"),
    ("tournament", lambda n: plural(n, "tournament")),
    ("event", lambda n: plural(n, "team event")),
]


def event_counts(week):
    """['2 practices', '1 dryland'] for the team events in a week's items."""
    return [text(n) for kind, text in EVENT_COUNTS
            if (n := sum(1 for it in week if it[4] == kind))]


def clock(t):
    """time(19, 10) -> '7:10 PM'."""
    return t.strftime("%I:%M %p").lstrip("0")


def maps_link(google, apple, css_class, text, label, body=None):
    """
    A directions link: Google Maps in the HTML, Apple Maps swapped in on iOS.
    With `body` (HTML, such as an icon) the text becomes the hover title.
    """
    apple_attr = f' data-apple-maps="{escape(apple)}"' if apple else ''
    title = f' title="{escape(text)}"' if body is not None else ''
    return (f'<a class="{css_class}" href="{escape(google)}"{apple_attr}{title} '
            f'target="_blank" rel="noopener noreferrer" aria-label="{escape(label)}">'
            f'{escape(text) if body is None else body}</a>')


def directions_link(rink, css_class, text, body=None):
    """A directions link for a GTHL rink, or nothing if its address is not known."""
    url = arenas.directions_url(rink)
    if not url:
        return ""
    arena = arenas.find(rink)
    return maps_link(url, arenas.apple_directions_url(rink), css_class, text,
                     f"Directions to {arena['name']}, {arenas.address(arena)}", body)


# The row's play icon, drawn in currentColor so the stylesheet sets their colour.
PLAY_ICON = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.5v9l7.5-4.5z"/></svg>'


LIVE_MINUTES = 60


def stream_state(start, now):
    """'upcoming', 'live' (the first hour from puck drop) or 'rewatch'."""
    minutes = (now - start).total_seconds() / 60
    if minutes < 0:
        return 'upcoming'
    return 'live' if minutes < LIVE_MINUTES else 'rewatch'


STREAM_TEXT = {'upcoming': 'Watch', 'live': 'Live', 'rewatch': 'Rewatch'}


def watch_link(game, start, now, css_class="game-watch", icon=False):
    """
    The GTHL's LiveBarn link for a game: nothing before puck drop, LIVE for the
    first hour, Rewatch after; in a row, a play icon. The link goes to the rink's camera at the game's
    date and start time, so it serves for both; LiveBarn needs its own
    subscription.

    The state written here is right when the page is built. The page's script
    recomputes it from data-start every minute, so LIVE switches on and off on
    time between the hourly rebuilds.
    """
    url = (game.get('Stream') or '').strip()
    if not url.startswith('https://livebarn.com/') or start is None:
        return ''
    state = stream_state(start, now)
    hidden = ' hidden' if state == 'upcoming' else ''
    label = f"{game.get('Away', '')} at {game.get('Home', '')} on LiveBarn"
    return (f'<a class="{css_class} is-{state}" href="{escape(url)}" target="_blank" '
            f'rel="noopener noreferrer" data-start="{start.isoformat()}" '
            f'data-label="{escape(label)}" aria-label="{STREAM_TEXT[state]}: {escape(label)}"{hidden}>'
            f'{PLAY_ICON if icon else STREAM_TEXT[state]}</a>')


def drawer(*parts):
    """
    The row's tap-to-open drawer: where (with directions) and, logged in,
    arrival time and what to wear. Parts are HTML; empty ones are dropped.
    Returns '' when there is nothing in it.
    """
    parts = [p for p in parts if p]
    if not parts:
        return ''
    return '<div class="game-extra game-details">' + "".join(parts) + '</div>'


def detail_text(text):
    return f'<span class="detail">{escape(text)}</span>' if text else ''


def live_flag(start, now):
    """
    "● LIVE" in place of the start time during a game's first hour. Written
    for the moment the page is built; the page's script keeps it current.
    """
    if start is None:
        return ''
    hidden = '' if stream_state(start, now) == 'live' else ' hidden'
    return f'<span class="game-live" data-live-start="{start.isoformat()}"{hidden}>Live</span>'


def row_icons(watch):
    """The LiveBarn play icon, between the teams and the score."""
    return f'<div class="game-icons">{watch}</div>' if watch else ''


def rink_cell(rink):
    """The rink for the drawer, as a directions link when its address is known."""
    linked = directions_link(rink, "game-rink", rink)
    return linked or (f'<span class="game-rink">{escape(rink)}</span>' if rink else '')


def venue_cell(venue, address, css_class="game-rink"):
    """A TeamSnap venue, linked to directions to TeamSnap's own address."""
    text = short_venue(venue) or (address or "")
    google, apple = arenas.address_urls(address)
    if google and text:
        return maps_link(google, apple, css_class, text, f"Directions to {text}, {address}")
    return f'<span class="{css_class}">{escape(text)}</span>' if text else ''


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


def row_attrs(classes, details, row_type="game", day=None, kind="game"):
    """
    The opening tag's attributes for a row. A row with details opens on tap.
    There is deliberately no visual cue; it stays focusable and announces
    itself as a toggle, so keyboards and screen readers still find it.

    `row_type` is what the Games / Practices filter goes by: "game",
    "practice" (ice and dryland) or "other".

    Our own rows start open, since their details are the ones a family
    needs; a tap still closes them.

    `day` and `kind` are for the page's script: the Week / Month / Season
    view goes by the date, and the week headings count by kind.
    """
    is_open = bool(details) and "is-ours" in classes.split()
    attrs = (f'class="{classes}{" has-details" if details else ""}{" is-open" if is_open else ""}" '
             f'data-type="{row_type}" data-kind="{kind}"'
             + (f' data-date="{day.isoformat()}"' if day else ''))
    if details:
        attrs += f' tabindex="0" role="button" aria-expanded="{str(is_open).lower()}"'
    return attrs


# The Games / Practices filter's grouping of team events.
ROW_TYPES = {"practice": "practice", "dryland": "practice", "tournament": "game"}




def arrival(event):
    return f"Arrive {event['arrive']}" if event and event.get("arrive") else ""


# --- Rows ---------------------------------------------------------------------

def game_row(game, day, our_team, team=None, start=None, now=None):
    """
    One league game as a compact row: day and time, then both teams stacked,
    then the LiveBarn play icon, then each team's goals once played. Ours look
    the same as everyone else's apart from the red bar. Where it is (with
    directions) and, logged in, arrival time and jersey are in the drawer a
    tap opens. During
    the first hour "LIVE" stands in for the start time.

    Once played, "Final" takes the time's place and the winner is in bold, so a
    score never reads as a time. Our games add a W, L or T. The GTHL writes the
    score as away:home, the order of its own columns.

    `team` is the matching TeamSnap entry, if any, which adds arrival time and
    jersey colour in the team version of the page.
    """
    away, home = game.get('Away', ''), game.get('Home', '')
    ours = our_team in (away.lower(), home.lower())
    score = parse_score(format_score(game.get('Score')))
    day_text = f"{day.strftime('%a')} {day.day}" if day else escape(game.get('Date', ''))

    def team_line(name, goals, other, row):
        classes = ['game-team', f'r{row}']
        if name.lower() == our_team:
            classes.append('us')
        result = ''
        if score is not None:
            result = 'won' if goals > other else 'lost' if goals < other else 'tied'
            classes.append(result)
        goals_html = (f'<span class="game-goals r{row} {result}">{goals}</span>'
                      if score is not None else '')
        return (f'<div class="{" ".join(classes)}">{page_common.team_logo(name)}'
                f'<span class="game-name">{escape(name)}</span></div>{goals_html}')

    rink_text = rink_cell(game.get('Arena', ''))
    icons = row_icons(watch_link(game, start, now, "icon-btn game-watch", icon=True))

    if score is not None:
        a, h = score['away'], score['home']
        status = '<span class="game-final">Final</span>'
        if ours:
            mine, theirs = (h, a) if home.lower() == our_team else (a, h)
            result = 'W' if mine > theirs else 'L' if mine < theirs else 'T'
            status += (f'<span class="game-result result-{result.lower()}" '
                       f'title="{ {"W": "Win", "L": "Loss", "T": "Tie"}[result] }">{result}</span>')
        when = f'<span class="game-time">{status}</span>'
        teams = team_line(away, a, h, 1) + team_line(home, h, a, 2)
        details = drawer(rink_text)
    else:
        when = (f'<span class="game-time">{escape(game.get("Time", ""))}</span>'
                + live_flag(start, now))
        teams = team_line(away, 0, 0, 1) + team_line(home, 0, 0, 2)
        details = drawer(rink_text, detail_text(arrival(team)),
                         detail_text(wear_text(team.get("wear"), True) if team else ""))

    live = score is None and start is not None and stream_state(start, now) == 'live'
    classes = f"game{' is-ours' if ours else ''}{' is-final' if score else ''}{' is-live' if live else ''}"
    return f"""                    <div {row_attrs(classes, details, day=day)}>
                        <div class="game-when"><span class="game-day">{day_text}</span>
                            {when}</div>
                        <div class="game-teams">{teams}{icons}{details}</div>
                    </div>
"""


def team_game_row(event, start, now=None):
    """A game only TeamSnap lists: exhibition, preseason or tournament."""
    us, them = config.TEAM_NAME, event["opponent"]
    away, home = (them, us) if event["home"] else (us, them)

    def team_line(name, row):
        cls = f'game-team r{row} us' if name == us else f'game-team r{row}'
        return (f'<div class="{cls}">{page_common.team_logo(name)}'
                f'<span class="game-name">{escape(name)}</span></div>')

    time_text = clock(start.time()) if event.get("timed") else "Time TBA"
    details = drawer(venue_cell(event.get("venue"), event.get("address")), detail_text(arrival(event)),
                     detail_text(wear_text(event.get("wear"), True)))
    begins = aware(start) if event.get("timed") else None
    flag = live_flag(begins, now) if now else ''
    live = bool(begins and now and stream_state(begins, now) == 'live')
    return f"""                    <div {row_attrs(f"game is-ours team-game{' is-live' if live else ''}", details, day=start.date())}>
                        <div class="game-when"><span class="game-day">{start.strftime('%a')} {start.day}</span>
                            <span class="game-time">{time_text}</span>{flag}</div>
                        <div class="game-teams">{team_line(away, 1)}{team_line(home, 2)}{extra_line(event.get("label"))}{details}</div>
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
    details = drawer(venue_cell(event.get("venue"), event.get("address")),
                     detail_text(arrival(event) if event.get("timed") else ""),
                     detail_text(wear))
    return f"""                    <div {row_attrs(f"game is-ours team-event kind-{kind}", details, ROW_TYPES.get(kind, "other"), start.date(), kind)}>
                        <div class="game-when"><span class="game-day">{start.strftime('%a')} {start.day}</span>
                            <span class="game-time">{time_text}</span></div>
                        <div class="game-teams"><div class="event-title r1">{tag}<span>{escape(title)}</span></div>{details}</div>
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


def aware(start):
    """A naive Toronto wall-clock datetime made timezone-aware, or None."""
    return start.replace(tzinfo=page_common.TORONTO) if start else None


def build_block(schedule, today, our_team, team_events=None, now=None):
    """
    The schedule itself: next-game card, heading with the filter, and the
    weeks. Without team_events this is the public version.
    """
    this_monday = today - timedelta(days=today.weekday())
    now = now or datetime.now(page_common.TORONTO)

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
        items.append((key, day, game_row(g, day, our_team, matches.get(i), aware(start), now),
                      is_ours(g), "game"))

    # Every team event: the page pages through the whole season.
    for e in team_events or []:
        if e["uid"] in used:
            continue
        start = datetime.fromisoformat(e["start"])
        if e["kind"] == "game":
            items.append((start, start.date(), team_game_row(e, start, now), True, "game"))
        else:
            items.append((start, start.date(), team_event_row(e, start), True, e["kind"]))
    items.sort(key=lambda it: it[0])

    # The next game, from the league schedule or, unlocked, any of ours.
    candidates = []
    for i, (g, day, start) in enumerate(league):
        if is_ours(g) and day and day >= today and not format_score(g.get('Score')):
            team = matches.get(i)
            rink = g.get('Arena', '')
            rink_html = (directions_link(rink, 'next-rink', rink) or f"<span>{escape(rink)}</span>") \
                + watch_link(g, aware(start), now, css_class="game-watch next-watch")
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
    logged_in = team_events is not None
    html += f"""
                <div class="sched-head{' has-type' if logged_in else ''}">
                    <h2>Schedule</h2>
                    <div class="sched-filter" role="group" aria-label="Which games to show">
                        <button type="button" class="sched-filter-btn" data-filter="ours"
                                aria-pressed="{str(default_ours).lower()}">{short_name}
                            <span class="sched-filter-count">{games_ours}</span></button>
                        <button type="button" class="sched-filter-btn" data-filter="all"
                                aria-pressed="{str(not default_ours).lower()}">All
                            <span class="sched-filter-count">{games_all}</span></button>
                    </div>
"""
    if logged_in:
        # Logged in only: there is nothing but games without the team events.
        # It shares the heading's line with the Eagles / All toggle.
        html += """
                    <div class="type-filter sched-filter" role="group" aria-label="What to show">
                    <button type="button" class="sched-filter-btn sched-type-btn" data-type-filter="game"
                            aria-pressed="false">Games</button>
                    <button type="button" class="sched-filter-btn sched-type-btn" data-type-filter="practice"
                            aria-pressed="false">Practices</button>
                    <button type="button" class="sched-filter-btn sched-type-btn" data-type-filter="all"
                            aria-pressed="true">All</button>
                    </div>
"""
    html += """
                </div>
"""
    html += period_bar(today)

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
        events = event_counts(week)

        def heading_count(games):
            # "0 games" only when there is nothing else to say about the week.
            parts = ([plural(games, 'game')] if games or not events else []) + events
            return " · ".join(parts)
        label = week_label(monday, this_monday) if monday else "Date to be confirmed"
        now = ' now' if monday == this_monday else ''
        has_ours = any(it[3] for it in week)
        week_attr = f' data-week="{monday.isoformat()}"' if monday else ''
        html += f"""                <section class="week" data-ours="{int(has_ours)}"{week_attr}>
                    <div class="week-head"><h3 class="week-label{now}">{label}</h3>
                        <span class="week-count"><span class="count-ours">{heading_count(g_ours)}</span><span
                            class="count-all">{heading_count(g_all)}</span></span></div>
                    <div class="week-games">
"""
        for it in week:
            html += it[2]
        html += "                    </div>\n                </section>\n"

    html += ('                <p class="sched-empty" data-sched-empty hidden></p>\n'
             "                </div>\n")
    return html


def period_bar(today):
    """
    Week / Month / Season, with arrows to step back and forward and a way back
    to today. The page's script does the work; without it the bar is hidden
    and every week shows, as before.
    """
    return f"""
                <div class="period-bar" data-period-bar data-today="{today.isoformat()}"
                     data-season="{escape(page_common.season_label().replace('-', '–'))}">
                    <div class="sched-filter period-pick" role="group" aria-label="How much to show">
                        <button type="button" class="sched-filter-btn" data-period="week" aria-pressed="false">Week</button>
                        <button type="button" class="sched-filter-btn" data-period="month" aria-pressed="true">Month</button>
                        <button type="button" class="sched-filter-btn" data-period="season" aria-pressed="false">Season</button>
                    </div>
                    <div class="period-nav">
                        <button type="button" class="period-today" data-period-today hidden>Today</button>
                        <button type="button" class="period-step" data-period-step="-1" aria-label="Previous"><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M8.5 3 4.5 7l4 4"/></svg></button>
                        <span class="period-label" data-period-label aria-live="polite"></span>
                        <button type="button" class="period-step" data-period-step="1" aria-label="Next"><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M5.5 3l4 4-4 4"/></svg></button>
                    </div>
                </div>
"""


def season_rows(schedule):
    """
    Games the season accumulator remembers that the current scrape no longer
    lists, as schedule rows. The GTHL is scraped a week back at most, so this
    is what lets the page page back through the season. A game the GTHL
    stopped listing inside the scrape window may be cancelled and is left out.
    """
    if not os.path.exists(season_schedule.SEASON_FILE):
        return []
    with open(season_schedule.SEASON_FILE, encoding="utf-8") as f:
        games = json.load(f).get("games", [])
    listed = {season_schedule.game_id(g) for g in schedule}
    rows = []
    for g in games:
        if g.get("id") in listed or g.get("status") == "not_listed" or not g.get("date"):
            continue
        day = datetime.strptime(g["date"], "%Y-%m-%d")
        when = datetime.strptime(g["time"], "%H:%M") if g.get("time") else None
        rows.append({
            "Date": f"{day.strftime('%d-%b-%Y')} {day.strftime('%a')}",
            "Time": clock(when.time()) if when else "",
            "Away": g.get("away", ""),
            "Home": g.get("home", ""),
            "Score": g.get("score_raw", ""),
            "Arena": g.get("arena", ""),
            "Stream": g.get("stream", ""),
        })
    return rows



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
    schedule = schedule + season_rows(schedule)
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

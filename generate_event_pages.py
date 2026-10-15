#!/usr/bin/env python3
"""
A page for every event on the team calendar that is not a league game:
practices, dryland, exhibition and tournament games, tournaments and anything
else. Tapping one on the schedule opens it: event-<hash>.html.

The team calendar is private, so each page is published encrypted with the
team password, exactly as the schedule's team events are (team_crypto.py).
Without the password a page says only that it is a team event and offers the
log-in; a phone that has logged in before opens it straight away. The file
name is a hash of TeamSnap's id and the title is generic, so neither gives
anything away. Pages are only built where the password and the calendar are
available, i.e. by the hourly workflow.

Each kind of event gets its own page:
  practice    when, how long, when to arrive, where
  dryland     the same, and what to wear
  game        a matchup like a league game's page, with the jersey colour
  tournament  the dates, where, and our games in it
  other       when and where
"""

import glob
import json
import os
from datetime import datetime, timedelta
from html import escape

import arenas
import config
import page_common
import team_crypto
from generate_schedule_html import (EVENT_TITLES, LOGIN_DIALOG, PLAY_ICON, aware, clock, countdown,
                                    event_page, event_stream, stream_state,
                                    load_team_events, maps_link, match_team_games, parse_game_date,
                                    parse_game_time, season_rows, short_venue, team_game_row,
                                    team_name_html)

# The label above an event's name; it says what kind of thing the name is.
KIND_LABELS = {"practice": "On-ice practice", "dryland": "Off-ice training", "game": "Game",
               "tournament": "Tournament", "event": "Team event"}

# Jersey and kit colours a swatch can show, by the word TeamSnap uses.
COLOURS = {"white": "#ffffff", "red": "#c8102e", "black": "#16181c", "blue": "#1f4e9c",
           "navy": "#1b2a4a", "grey": "#8a8d93", "gray": "#8a8d93", "green": "#2e7d32",
           "yellow": "#f2c230", "gold": "#c9a227", "orange": "#e07b1a"}


def start_of(event):
    return datetime.fromisoformat(event["start"])


def end_of(event):
    return datetime.fromisoformat(event["end"]) if event.get("end") else None


def duration(event):
    """'1 h 30 min', or '' when TeamSnap gives no real length."""
    end = end_of(event)
    if not event.get("timed") or not end:
        return ""
    minutes = int((end - start_of(event)).total_seconds() // 60)
    if minutes <= 0:
        return ""
    h, m = divmod(minutes, 60)
    return " ".join(x for x in (f"{h} h" if h else "", f"{m} min" if m else "") if x)


def last_day(event):
    """The last day an event covers; an all-day end at midnight is exclusive."""
    start, end = start_of(event), end_of(event)
    if not end or end.date() <= start.date():
        return start.date()
    if not event.get("timed") and end.time() == datetime.min.time():
        return end.date() - timedelta(days=1)
    return end.date()


def status(event, now, today):
    """Happening now, done, or a countdown."""
    start = start_of(event)
    if event.get("timed") and event.get("end"):
        begins, ends = aware(start), aware(end_of(event))
        if begins <= now < ends:
            return '<span class="match-status live">Happening now</span>'
        if now >= ends:
            return '<span class="match-status">Done</span>'
    elif start.date() <= today <= last_day(event) and last_day(event) > start.date():
        return '<span class="match-status live">On now</span>'
    elif last_day(event) < today:
        return '<span class="match-status">Done</span>'
    return f'<span class="match-status upcoming">{escape(countdown(start.date(), today))}</span>'


def time_range(event):
    start, end = start_of(event), end_of(event)
    if not event.get("timed"):
        last = last_day(event)
        if last > start.date():
            return f"{start.strftime('%a %b')} {start.day} – {last.strftime('%a %b')} {last.day}"
        return "All day"
    text = clock(start.time())
    if end and end > start and end.date() == start.date():
        text += f" – {clock(end.time())}"
    return text


def swatch(wear):
    """A colour dot for the first colour word in what to wear."""
    for word in (wear or "").lower().replace("/", " ").split():
        if word in COLOURS:
            return f'<span class="swatch" style="background:{COLOURS[word]}"></span>'
    return ""


def tile(label, value, note=""):
    return (f'<div class="scout-tile"><span class="scout-label">{escape(label)}</span>'
            f'<span class="scout-value">{value}</span>'
            + (f'<span class="scout-note">{escape(note)}</span>' if note else "") + '</div>')


# --- Sections -------------------------------------------------------------------

def hero(event, now, today):
    kind = event["kind"]
    start = start_of(event)
    label = event.get("label") if kind == "game" else KIND_LABELS.get(kind, "Team event")
    top = (f'<div class="match-top"><span>{escape(label or "Game")}</span>'
           f'{status(event, now, today)}</div>')
    when = f'{start.strftime("%A, %B")} {start.day}'
    if kind == "game":
        us, them = config.TEAM_NAME, event["opponent"]
        away, home = (them, us) if event["home"] else (us, them)

        def side(team, role):
            return f"""<div class="match-team{' us' if team == us else ''}">
                        {page_common.team_logo(team)}
                        <span class="match-name">{team_name_html(team)}</span>
                        <span class="match-role">{role}</span>
                    </div>"""
        middle = (f'<div class="match-time"><span>{escape(clock(start.time()) if event.get("timed") else "TBA")}</span>'
                  f'<span class="match-date">{start.strftime("%a, %b")} {start.day}</span></div>')
        body = (f'<div class="match-face">{side(away, "Away")}<div class="match-middle">{middle}</div>'
                f'{side(home, "Home")}</div>')
    else:
        title = EVENT_TITLES.get(kind) or event["title"]
        body = (f'<div class="event-head"><h2 class="event-name">{escape(title)}</h2>'
                f'<p class="event-when">{when} · {escape(time_range(event))}</p></div>')
    return f"""
                <section class="match-hero event-hero kind-{kind}">
                    {top}
                    {body}
                </section>
"""


def facts(event):
    kind = event["kind"]
    start = start_of(event)
    tiles = [tile("When", f'{start.strftime("%a, %b")} {start.day}', time_range(event))]
    if duration(event):
        tiles.append(tile("On the ice" if kind in ("practice", "game") else "Length",
                          escape(duration(event))))
    if event.get("arrive") and event.get("timed"):
        early = int((start - datetime.combine(start.date(),
                                              datetime.strptime(event["arrive"], "%I:%M %p").time())
                     ).total_seconds() // 60)
        tiles.append(tile("Arrive", escape(event["arrive"]),
                          f"{early} min before" if early > 0 else ""))
    if event.get("wear") and kind != "practice":
        label = "Jersey" if kind == "game" else "Wear"
        tiles.append(tile(label, swatch(event["wear"]) + escape(event["wear"].capitalize())))
    return f"""
                <section class="team-block">
                    <div class="scout-grid">{"".join(tiles)}</div>
                </section>
"""


def watch(event, now):
    """LiveBarn for a game at a pad we know (see livebarn.py)."""
    url = event_stream(event)
    if not url:
        return ""
    state = stream_state(aware(start_of(event)), now)
    text = {"upcoming": "Watch live on LiveBarn", "live": "Live now on LiveBarn",
            "rewatch": "Rewatch on LiveBarn"}[state]
    return (f'\n                <div class="match-actions"><a class="match-btn watch is-{state}" '
            f'href="{escape(url)}" target="_blank" rel="noopener noreferrer">{PLAY_ICON}'
            f'<span>{text}</span></a></div>\n')


def where(event):
    venue = short_venue(event.get("venue"))
    address = event.get("address")
    if not venue and not address:
        return """
                <section class="team-block">
                    <div class="block-head"><h3>Where</h3></div>
                    <p class="team-empty">Location to be confirmed.</p>
                </section>
"""
    google, apple = arenas.address_urls(address)
    name = venue or address
    place = (maps_link(google, apple, "match-place", name, f"Directions to {name}, {address}")
             if google else escape(name))
    sub = f'<span class="match-sub">{escape(address)}</span>' if address and venue else ""
    button = (maps_link(google, apple, "match-btn", "Directions", f"Directions to {name}, {address}")
              if google else "")
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Where</h3></div>
                    <div class="facts"><div class="fact"><span class="fact-label">Venue</span>
                        <span class="fact-value">{place}{sub}</span></div></div>
                    {f'<div class="match-actions event-actions">{button}</div>' if button else ''}
                </section>
"""


def tournament_games(event, events, now):
    """Our games inside a tournament's dates, from the team calendar."""
    first, last = start_of(event).date(), last_day(event)
    games = [e for e in events if e["kind"] == "game" and first <= start_of(e).date() <= last]
    if not games:
        return """
                <section class="team-block">
                    <div class="block-head"><h3>Our games</h3></div>
                    <p class="team-empty">Game times are not on the team calendar yet.</p>
                </section>
"""
    rows = "".join(team_game_row(e, start_of(e), now) for e in games)
    return f"""
                <section class="team-block">
                    <div class="block-head"><h3>Our games</h3><span>{len(games)} on the team calendar</span></div>
                    <div class="team-games"><div class="week-games">
{rows}                    </div></div>
                </section>
"""


def detail(event, events, now, today):
    html = hero(event, now, today) + watch(event, now) + facts(event) + where(event)
    if event["kind"] == "tournament":
        html += tournament_games(event, events, now)
    return html


# --- Assembly -------------------------------------------------------------------

LOCKED = """
                <section class="team-block event-locked">
                    <h2>Team event</h2>
                    <p>Practices, dryland and team events are for the team. Log in with the
                    team password to see this one.</p>
                    <a class="match-btn" href="#login" data-open-login>Team Login</a>
                </section>
"""


def page(sealed, timestamp):
    payload = json.dumps(sealed).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Team event - {config.SITE_TITLE}</title>
    <meta name="robots" content="noindex">
{page_common.FONT_LINK}
{page_common.FAVICON_LINKS}
    <style>
{page_common.PAGE_CSS}{page_common.TEAM_CSS}{page_common.GAME_CSS}{page_common.EVENT_CSS}    </style>
</head>
<body>
    <div class="container">
{page_common.masthead("schedule.html", page_common.division_label(), page_common.season_label())}

        <div class="content">
            <div class="team-page">
                <a class="team-back" href="schedule.html">&#8249; Schedule</a>
                <div class="event-body" data-schedule-block>{LOCKED}</div>
            </div>
{page_common.freshness(timestamp)}            <script type="application/json" id="team-events">{payload}</script>
{LOGIN_DIALOG}        </div>

{page_common.page_end()}    </div>
{page_common.SCHEDULE_JS}</body>
</html>
"""


def generate(today=None):
    events, password = load_team_events()
    if events is None:
        print("Event pages skipped: no team calendar or password")
        return []
    with open("schedule.json", encoding="utf-8") as f:
        data = json.load(f)
    schedule = data.get("schedule", [])
    rows = schedule + season_rows(schedule)
    league = []
    for g in rows:
        day = parse_game_date(g.get("Date", ""))
        t = parse_game_time(g.get("Time", ""))
        league.append((g, day, datetime.combine(day, t) if day and t else None))
    _, used = match_team_games(league, events, config.TEAM_NAME.lower())
    now = datetime.now(page_common.TORONTO)
    today = today or now.date()
    sealer = team_crypto.Sealer(password)
    written = []
    for e in events:
        if e["uid"] in used:
            continue   # A league game: it has its own public game page.
        name = event_page(e)
        with open(name, "w", encoding="utf-8") as f:
            f.write(page(sealer.seal(detail(e, events, now, today)), data.get("timestamp", "")))
        written.append(name)
    for stale in set(glob.glob("event-*.html")) - set(written):
        os.remove(stale)
    games = [e for e in events if e["kind"] == "game" and e["uid"] not in used]
    # Counts only: the log of a public repository is public.
    print(f"Generated {len(written)} event pages; LiveBarn for "
          f"{sum(1 for e in games if event_stream(e))} of {len(games)} team-calendar games")
    return written


if __name__ == "__main__":
    generate()

#!/usr/bin/env python3
"""
Generate HTML page from scraped schedule data
"""

import json
from datetime import datetime, timedelta
from html import escape

import config
import page_common


def parse_game_date(raw):
    """'12-Oct-2026 Mon' -> date(2026, 10, 12), or None if unreadable."""
    try:
        return datetime.strptime(raw.split()[0], "%d-%b-%Y").date()
    except (ValueError, IndexError, AttributeError):
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


def next_game_card(game, day, today):
    """The card for the next Eagles game: both teams, when and where."""
    away, home = game.get('Away', ''), game.get('Home', '')
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
                        <span><strong>{escape(game.get('Time', ''))}</strong></span>
                        <span>{escape(game.get('Arena', ''))}</span>
                    </div>
                </section>
"""


def game_row(game, day, our_team):
    """
    One game as a compact row: day and time, both teams stacked, the rink.
    Ours look the same as everyone else's apart from the red bar.
    """
    away, home = game.get('Away', ''), game.get('Home', '')
    ours = our_team in (away.lower(), home.lower())
    when = escape(format_score(game.get('Score')) or game.get('Time', ''))
    day_text = f"{day.strftime('%a')} {day.day}" if day else escape(game.get('Date', ''))

    def team(name):
        us = ' us' if name.lower() == our_team else ''
        return (f'<div class="game-team{us}">{page_common.team_logo(name)}'
                f'<span>{escape(name)}</span></div>')

    return f"""                    <div class="game{' is-ours' if ours else ''}">
                        <div class="game-when"><span class="game-day">{day_text}</span>
                            <span class="game-time">{when}</span></div>
                        <div class="game-teams">{team(away)}{team(home)}</div>
                        <div class="game-rink">{escape(game.get('Arena', ''))}</div>
                    </div>
"""


def group_by_week(games):
    """
    [(monday, [(game, day), ...]), ...] in the order the GTHL lists games.

    A game whose date cannot be read gets a group of its own, under a None
    week, rather than being dropped.
    """
    weeks = []
    for game, day in games:
        monday = day - timedelta(days=day.weekday()) if day else None
        if weeks and monday is not None and weeks[-1][0] == monday:
            weeks[-1][1].append((game, day))
        else:
            weeks.append((monday, [(game, day)]))
    return weeks


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
    this_monday = today - timedelta(days=today.weekday())

    def is_ours(game):
        return our_team in (game.get('Away', '').lower(), game.get('Home', '').lower())

    ours_count = sum(1 for g in schedule if is_ours(g))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.SITE_TITLE} - Schedule</title>
{page_common.FONT_LINK}
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
        games = [(g, parse_game_date(g.get('Date', ''))) for g in schedule]
        html += '            <div class="schedule">\n'

        upcoming = next(((g, d) for g, d in games
                         if is_ours(g) and d and d >= today
                         and not format_score(g.get('Score'))), None)
        if upcoming:
            html += next_game_card(upcoming[0], upcoming[1], today)

        # Default to our own games, unless there are none to show.
        default_ours = ours_count > 0
        short_name = config.TEAM_NAME.split()[-1]
        html += f"""
                <div class="sched-head">
                    <h2>Schedule</h2>
                    <div class="sched-filter" role="group" aria-label="Which games to show">
                        <button type="button" class="sched-filter-btn" data-filter="ours"
                                aria-pressed="{str(default_ours).lower()}">{short_name}
                            <span class="sched-filter-count">{ours_count}</span></button>
                        <button type="button" class="sched-filter-btn" data-filter="all"
                                aria-pressed="{str(not default_ours).lower()}">All
                            <span class="sched-filter-count">{len(schedule)}</span></button>
                    </div>
                </div>

                <div class="sched-weeks{' filter-ours' if default_ours else ''}"
                     data-schedule-view data-has-ours="{int(bool(ours_count))}">
"""

        for monday, items in group_by_week(games):
            n_ours = sum(1 for g, _ in items if is_ours(g))
            label = week_label(monday, this_monday) if monday else "Date to be confirmed"
            now = ' now' if monday == this_monday else ''
            html += f"""                <section class="week" data-ours="{int(bool(n_ours))}">
                    <div class="week-head"><h3 class="week-label{now}">{label}</h3>
                        <span class="week-count"><span class="count-ours">{plural(n_ours, 'game')}</span><span
                            class="count-all">{plural(len(items), 'game')}</span></span></div>
"""
            html += '                    <div class="week-games">\n'
            for game, day in items:
                html += game_row(game, day, our_team)
            html += "                    </div>\n                </section>\n"

        html += f"""                </div>
{page_common.freshness(timestamp)}            </div>
"""

    html += f"""        </div>

{page_common.page_end()}    </div>
{page_common.SCHEDULE_JS}</body>
</html>
"""

    # Write to file
    with open('schedule.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("Generated schedule.html")


if __name__ == '__main__':
    generate_html()

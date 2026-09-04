#!/usr/bin/env python3
"""
Generate HTML page from scraped schedule data
"""

import json
from datetime import datetime

import config
import page_common


def format_game_date(raw):
    """'12-Oct-2026 Mon' -> 'Mon, Oct 12', for the date heading above a group."""
    try:
        parsed = datetime.strptime(raw.split()[0], "%d-%b-%Y")
    except (ValueError, IndexError):
        return raw
    return f"{parsed.strftime('%a, %b')} {parsed.day}"


def format_score(raw):
    """
    The score, or nothing at all if the game has not been played.

    The GTHL writes an unplayed game's score as a bare ':' separator, which
    reads as a broken cell rather than as "no result yet".
    """
    cleaned = (raw or "").strip()
    return "" if cleaned in ("", ":") else cleaned


def generate_html():
    """Generate HTML page from schedule.json"""

    # Load schedule data
    with open('schedule.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    schedule = data.get('schedule', [])
    timestamp = data.get('timestamp', '')
    filters = data.get('filters', {})
    error = data.get('error')

    our_team = config.TEAM_NAME.lower()

    def is_ours(game):
        return (our_team in game.get('Away', '').lower()
                or our_team in game.get('Home', '').lower())

    ours_count = sum(1 for g in schedule if is_ours(g))

    # Drop columns that say nothing. Before a game is played every Score cell
    # is empty, and a division playing only league games has "LG" on every
    # row; both are a column of noise on a phone and a column of nothing on a
    # laptop. They come back on their own once the data varies.
    show_score = any(format_score(g.get('Score')) for g in schedule)
    show_type = len({g.get('Type', '') for g in schedule}) > 1
    span = 4 + show_score + show_type

    # Start building HTML (EXACT copy of standings structure)
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
"""
    elif not schedule:
        html += f"""
            <div class="notice">
                <h2>No games scheduled</h2>
                <p>The GTHL has not posted any {config.DIVISION} {config.CATEGORY}
                games between {filters.get('from_date', '')} and
                {filters.get('to_date', '')}.</p>
            </div>
"""
    else:
        # One table, two shapes: columns on a laptop, one card per game on a
        # phone. Games sit under a date heading either way, so the date is
        # written once per day instead of on every row.
        # Default to our own games, unless there are none to show.
        default_ours = ours_count > 0
        html += f"""
            <div class="sched-bar">
                <div class="sched-filter" role="group" aria-label="Which games to show">
                    <button type="button" class="sched-filter-btn" data-filter="ours"
                            aria-pressed="{str(default_ours).lower()}">{config.TEAM_NAME.split()[-1]}
                        <span class="sched-filter-count">{ours_count}</span></button>
                    <button type="button" class="sched-filter-btn" data-filter="all"
                            aria-pressed="{str(not default_ours).lower()}">All
                        <span class="sched-filter-count">{len(schedule)}</span></button>
                </div>
            </div>

            <div class="table-wrapper{' filter-ours' if default_ours else ''}"
                 data-schedule-view data-has-ours="{int(bool(ours_count))}">
                <table class="schedule-table{' has-rail' if (show_score or show_type) else ''}">
                    <thead>
                        <tr>
                            <th class="cell-time">Time</th>
                            <th class="cell-away">Away</th>
"""
        if show_score:
            html += '                            <th class="cell-score stat">Score</th>\n'
        html += """                            <th class="cell-home">Home</th>
                            <th class="cell-arena">Arena</th>
"""
        if show_type:
            html += '                            <th class="cell-type">Type</th>\n'
        html += """                        </tr>
                    </thead>
                    <tbody>
"""

        current_date = None

        for game in schedule:
            date = game.get('Date', '')
            away = game.get('Away', '')
            home = game.get('Home', '')
            score = format_score(game.get('Score'))

            if date != current_date:
                current_date = date
                # A day with none of our games is hidden along with its games
                # when the list is filtered, so the heading has to know.
                day_has_ours = int(any(
                    g.get('Date') == date and is_ours(g) for g in schedule))
                html += ('                        <tr class="date-row" '
                         f'data-ours="{day_has_ours}">'
                         f'<th colspan="{span}" class="date-head">'
                         f'{format_game_date(date)}</th></tr>\n')

            our_game = is_ours(game)
            row_class = 'game is-ours highlight' if our_game else 'game'

            html += f"""                        <tr class="{row_class}">
                            <td class="cell-time">{game.get('Time', '')}</td>
                            <td class="cell-away team-name">{away}</td>
"""
            if show_score:
                html += f'                            <td class="cell-score stat">{score}</td>\n'
            html += f"""                            <td class="cell-home team-name">{home}</td>
                            <td class="cell-arena">{game.get('Arena', '')}</td>
"""
            if show_type:
                html += f'                            <td class="cell-type">{game.get("Type", "")}</td>\n'
            html += "                        </tr>\n"

        html += """                    </tbody>
                </table>
            </div>
"""

    html += f"""{page_common.freshness(timestamp)}        </div>

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

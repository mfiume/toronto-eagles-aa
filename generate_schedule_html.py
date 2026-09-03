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

    formatted_time = page_common.format_timestamp(timestamp)

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
</head>
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
        html += """
            <div class="table-wrapper">
                <table class="schedule-table">
                    <thead>
                        <tr>
                            <th class="cell-time">Time</th>
                            <th class="cell-away">Away</th>
                            <th class="cell-score stat">Score</th>
                            <th class="cell-home">Home</th>
                            <th class="cell-arena">Arena</th>
                            <th class="cell-type">Type</th>
                        </tr>
                    </thead>
                    <tbody>
"""

        our_team = config.TEAM_NAME.lower()
        current_date = None

        for game in schedule:
            date = game.get('Date', '')
            away = game.get('Away', '')
            home = game.get('Home', '')
            score = format_score(game.get('Score'))

            if date != current_date:
                current_date = date
                html += ('                        <tr class="date-row">'
                         f'<th colspan="6" class="date-head">{format_game_date(date)}'
                         '</th></tr>\n')

            is_our_game = our_team in away.lower() or our_team in home.lower()
            row_class = 'game highlight' if is_our_game else 'game'

            html += f"""                        <tr class="{row_class}">
                            <td class="cell-time">{game.get('Time', '')}</td>
                            <td class="cell-away team-name">{away}</td>
                            <td class="cell-score stat">{score}</td>
                            <td class="cell-home team-name">{home}</td>
                            <td class="cell-arena">{game.get('Arena', '')}</td>
                            <td class="cell-type">{game.get('Type', '')}</td>
                        </tr>
"""

        html += """                    </tbody>
                </table>
            </div>
"""

    html += f"""        </div>

        <footer>
            <p>Last updated: {formatted_time}</p>
            <p>Updates hourly</p>
        </footer>
    </div>
</body>
</html>
"""

    # Write to file
    with open('schedule.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("Generated schedule.html")


if __name__ == '__main__':
    generate_html()

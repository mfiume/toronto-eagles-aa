#!/usr/bin/env python3
"""
Generate HTML page from scraped schedule data
"""

import json

import config
import page_common


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
        # Build table
        html += """
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Time</th>
                            <th>Away</th>
                            <th class="stat">Score</th>
                            <th>Home</th>
                            <th>Arena</th>
                            <th>Type</th>
                        </tr>
                    </thead>
                    <tbody>
"""

        # Add rows
        for game in schedule:
            date = game.get('Date', '')
            time = game.get('Time', '')
            away = game.get('Away', '')
            home = game.get('Home', '')
            score = game.get('Score', ':')
            arena = game.get('Arena', '')
            game_type = game.get('Type', '')

            # Highlight our own games
            our_team = config.TEAM_NAME.lower()
            is_our_game = our_team in away.lower() or our_team in home.lower()
            row_class = ' class="highlight"' if is_our_game else ''

            html += f"                        <tr{row_class}>\n"
            html += f"                            <td>{date}</td>\n"
            html += f"                            <td>{time}</td>\n"
            html += f'                            <td class="team-name">{away}</td>\n'
            html += f'                            <td class="stat">{score}</td>\n'
            html += f'                            <td class="team-name">{home}</td>\n'
            html += f"                            <td>{arena}</td>\n"
            html += f"                            <td>{game_type}</td>\n"
            html += "                        </tr>\n"

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

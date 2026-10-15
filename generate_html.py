#!/usr/bin/env python3
"""
Generate HTML page from standings JSON data
"""

import json

import config
import page_common
from season_schedule import slug

# Before a team has played, the GTHL leaves its record columns blank. With no
# games played a record is 0-0-0 by definition, so say so; the averages and the
# streak have no value yet and get a dash rather than a made-up zero.
RECORD_COLUMNS = {"W-L-T", "Home", "Away", "P10"}
NO_VALUE_YET = {"WIN%", "GFA", "GAA", "Streak"}


def before_first_game(row):
    """The row with its unplayed blanks filled in, for display only."""
    if str(row.get("GP", "")).strip() != "0":
        return row
    filled = dict(row)
    for key, value in row.items():
        if not str(value).strip():
            if key in RECORD_COLUMNS:
                filled[key] = "0-0-0"
            elif key in NO_VALUE_YET:
                filled[key] = "–"
    return filled


def column_classes(header, *extra):
    """The class attribute for a standings column."""
    names = [c for c in extra if c]
    return f' class="{" ".join(names)}"' if names else ""


def generate_html():
    """Generate HTML page from standings.json"""

    # Load standings data
    try:
        with open("standings.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: standings.json not found")
        return

    # Extract data
    standings = page_common.rank_standings(data.get("standings", []))
    timestamp = data.get("timestamp", "")
    filters = data.get("filters", {})
    error = data.get("error")

    # Start building HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.SITE_TITLE} - Standings</title>
{page_common.FONT_LINK}
{page_common.FAVICON_LINKS}
    <style>
{page_common.PAGE_CSS}{page_common.TEAM_CSS}    </style>
</head>
<body>
    <div class="container">
{page_common.masthead("index.html", page_common.division_label(filters), page_common.season_label())}

        <div class="content">
"""

    if error:
        html += f"""
            <div class="error">
                <h2>Error Loading Standings</h2>
                <p>{error}</p>
                <p>The scraper will try again during the next scheduled run.</p>
            </div>
"""
    elif not standings:
        html += page_common.season_not_started_notice("standings")
    else:
        # Build table
        html += """
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
"""

        # Get headers from first row
        if standings:
            headers = list(standings[0].keys())
            for header in headers:
                if not header or header == 'Logo' or header in page_common.RANK_FIELDS:
                    continue
                if header == 'Position':
                    # Unlabelled rank column.
                    html += '                            <th class="stat rank"></th>\n'
                elif header == 'Team':
                    html += f'                            <th class="team-col">{header}</th>\n'
                else:
                    # Every other standings column is a number.
                    attrs = column_classes(header, 'stat')
                    html += f'                            <th{attrs}>{header}</th>\n'

        html += """                        </tr>
                    </thead>
                    <tbody>
"""

        # Add rows
        for row in standings:
            # Mark our own row. The team comes from config like everywhere else.
            is_our_team = row.get('Team', '').lower() == config.TEAM_NAME.lower()
            row_class = ' class="highlight"' if is_our_team else ''
            html += f"                        <tr{row_class}>\n"
            for i, (key, value) in enumerate(before_first_game(row).items()):
                # Skip empty column names
                if key == '' or key in page_common.RANK_FIELDS:
                    continue

                # Handle Position column specially
                if key == 'Position':
                    # The place, shared ("T5") when the tie-breakers cannot separate teams.
                    html += f'                            <td class="stat rank">{page_common.rank_label(row)}</td>\n'
                elif key == 'Logo':
                    continue  # Skip Logo column, it will be included with Team
                elif key == 'Team':  # Team name
                    logo = page_common.team_logo(value, row.get('Logo'))
                    # The team's name leads to its own page.
                    html += (f'                            <td class="team-name">'
                             f'<a class="team-link" href="team-{slug(value)}.html">'
                             f'<span class="team-cell">{logo}<span>{value}</span></span></a></td>\n')
                elif key in ['DIFF', 'GD', '+/-']:  # Goal differential
                    try:
                        diff_val = int(value) if value else 0
                        sign = "positive" if diff_val > 0 else ("negative" if diff_val < 0 else "")
                        display_val = f"+{diff_val}" if diff_val > 0 else str(diff_val)
                        attrs = column_classes(key, 'stat', sign)
                        html += f'                            <td{attrs}>{display_val}</td>\n'
                    except ValueError:
                        html += f'                            <td{column_classes(key, "stat")}>{value}</td>\n'
                else:  # Other stats
                    attrs = column_classes(key, 'stat')
                    html += f'                            <td{attrs}>{value}</td>\n'
            html += "                        </tr>\n"

        html += """                    </tbody>
                </table>
            </div>
"""

    html += f"""{page_common.freshness(timestamp)}        </div>

{page_common.page_end()}    </div>
</body>
</html>
"""

    # Write HTML file
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("HTML page generated: index.html")

if __name__ == "__main__":
    generate_html()

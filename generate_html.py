#!/usr/bin/env python3
"""
Generate HTML page from standings JSON data
"""

import json

import config
import page_common

# Which standings columns survive a narrow screen. A phone shows the five that
# answer "where are we and how did we get there"; the rest come back as the
# screen widens, so nothing has to scroll sideways to be read.
#   (no class) always visible
#   col-md     from 620px
#   col-lg     from 1000px
COLUMN_TIER = {
    "WIN%": "col-md",
    "Streak": "col-md",
    "GFA": "col-lg",
    "GAA": "col-lg",
    "Home": "col-lg",
    "Away": "col-lg",
    "P10": "col-lg",
}


def column_classes(header, *extra):
    """The class attribute for a standings column, tier included."""
    names = [c for c in extra if c]
    tier = COLUMN_TIER.get(header)
    if tier:
        names.append(tier)
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
    standings = data.get("standings", [])
    timestamp = data.get("timestamp", "")
    filters = data.get("filters", {})
    error = data.get("error")

    formatted_time = page_common.format_timestamp(timestamp)

    # Start building HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.SITE_TITLE} - Standings</title>
{page_common.FONT_LINK}
    <style>
{page_common.PAGE_CSS}    </style>
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
                if not header or header == 'Logo':
                    continue
                if header == 'Position':
                    # Unlabelled rank column.
                    html += '                            <th class="stat rank"></th>\n'
                elif header == 'Team':
                    html += f"                            <th>{header}</th>\n"
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
            for i, (key, value) in enumerate(row.items()):
                # Skip empty column names
                if key == '':
                    continue

                # Handle Position column specially
                if key == 'Position':
                    html += f'                            <td class="stat rank">{value}</td>\n'
                elif key == 'Logo':
                    continue  # Skip Logo column, it will be included with Team
                elif key == 'Team':  # Team name
                    logo_url = row.get('Logo')
                    logo = (f'<img src="{logo_url}" alt="" class="team-logo" '
                            'onerror="this.style.display=\'none\'">') if logo_url else ''
                    html += (f'                            <td class="team-name">'
                             f'<span class="team-cell">{logo}<span>{value}</span></span></td>\n')
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

    html += f"""        </div>

        <footer>
            <p>Last updated: {formatted_time}</p>
            <p>Updates hourly</p>
        </footer>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("HTML page generated: index.html")

if __name__ == "__main__":
    generate_html()

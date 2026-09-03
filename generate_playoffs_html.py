#!/usr/bin/env python3
"""
Generate HTML page showing the playoff picture based on current standings.

The GTHL publishes the playoff structure per division per season and it is not
derivable from the standings, so the structure comes from config.PLAYOFF_FORMAT.
When that is unset, the page says the format has not been published rather than
seeding teams into last season's brackets.
"""

import json

import config
import page_common


def ordinal(n):
    """1 -> 1st, 2 -> 2nd, 13 -> 13th."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def render_team_table(teams, radius=None):
    """One standings table for a playoff group, our own team highlighted."""
    style = f' style="border-radius: {radius};"' if radius else ""
    html = f"""                <div class="table-wrapper"{style}>
                    <table>
                        <thead>
                            <tr>
                                <th class="rank">#</th>
                                <th>Team</th>
                                <th class="stat">GP</th>
                                <th class="stat">W-L-T</th>
                                <th class="stat">PTS</th>
                                <th class="stat">WIN%</th>
                            </tr>
                        </thead>
                        <tbody>
"""

    for team in teams:
        is_our_team = team.get("Team", "").lower() == config.TEAM_NAME.lower()
        row_class = ' class="highlight"' if is_our_team else ""
        html += f"""                            <tr{row_class}>
                                <td class="rank">{team.get('Position', '')}</td>
                                <td class="team-name">
                                    <img src="{team.get('Logo', '')}" alt="" class="team-logo" onerror="this.style.display='none'">
                                    <span>{team.get('Team', '')}</span>
                                </td>
                                <td class="stat">{team.get('GP', '')}</td>
                                <td class="stat">{team.get('W-L-T', '')}</td>
                                <td class="stat">{team.get('PTS', '')}</td>
                                <td class="stat">{team.get('WIN%', '')}</td>
                            </tr>
"""

    html += """                        </tbody>
                    </table>
                </div>
"""
    return html


def generate_html():
    """Generate HTML page from standings.json showing playoff picture"""

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

    formatted_time = page_common.format_timestamp(timestamp)

    # Seed teams into the configured playoff structure. Without a format, or
    # without standings, there is nothing to seed and the page says so.
    playoff_format = config.PLAYOFF_FORMAT
    can_seed = bool(playoff_format) and bool(standings)

    playoffs_direct = []
    pools = {}

    if can_seed:
        direct_cutoff = playoff_format["direct_cutoff"]
        pool_positions = playoff_format["pools"]

        playoffs_direct = [t for t in standings
                           if t.get("Position", 0) <= direct_cutoff]

        for pool_name, positions in pool_positions.items():
            pools[pool_name] = sorted(
                (t for t in standings if t.get("Position", 0) in set(positions)),
                key=lambda t: t.get("Position", 0),
            )

    # Start building HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.SITE_TITLE} - Playoffs</title>
{page_common.FONT_LINK}
    <style>
{page_common.PAGE_CSS}{page_common.PLAYOFF_CSS}    </style>
</head>
<body>
    <div class="container">
{page_common.masthead("playoffs.html", page_common.division_label(), page_common.season_label())}

        <div class="content">
"""

    if not playoff_format:
        html += f"""
            <div class="notice">
                <h2>Playoff format not published yet</h2>
                <p>The GTHL has not published the {config.DIVISION} {config.CATEGORY}
                {config.REGION} playoff structure for {config.SEASON}. This page fills
                in with the seeding picture once the format is out and games have
                been played.</p>
            </div>
"""
    elif not standings:
        html += page_common.season_not_started_notice("standings")
    else:
        html += """
            <div class="info-box">
"""
        html += f"""                <h3>{config.DIVISION} {config.CATEGORY} {config.REGION} Playoff Format</h3>
"""
        for note in playoff_format.get("notes", []):
            html += f"""                <p>{note}</p>
"""
        html += """            </div>
"""

        # Direct to the first round
        html += f"""
            <div class="section">
                <div class="section-header playoffs">
                    First Round (Direct to Playoffs)
                    <span class="badge">TOP {playoff_format["direct_cutoff"]}</span>
                </div>
"""
        html += render_team_table(playoffs_direct)
        html += """            </div>
"""

        # Play-in pools
        if pools:
            pool_positions = playoff_format["pools"]
            spread = sorted(p for positions in pool_positions.values() for p in positions)
            html += f"""
            <div class="section">
                <div class="section-header playins">
                    Preliminary Round (Play-ins)
                    <span class="badge">{ordinal(spread[0])} &ndash; {ordinal(spread[-1])}</span>
                </div>
"""
            for pool_name, teams in pools.items():
                positions = ", ".join(ordinal(p) for p in pool_positions[pool_name])
                html += f"""
                <div class="section-subheader">Pool {pool_name} <span class="pool-label">{positions}</span></div>
"""
                html += render_team_table(teams, radius="0")
            html += """            </div>
"""

    # Footer
    html += f"""        </div>

        <footer>
            <p>Based on current standings as of: {formatted_time}</p>
            <p>Playoff seeding updates hourly</p>
        </footer>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open("playoffs.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("HTML page generated: playoffs.html")


if __name__ == "__main__":
    generate_html()

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
                                <th>#</th>
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
                                <td>{team.get('Position', '')}</td>
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
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            padding: 0;
            color: #000000;
        }}

        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: #ffffff;
        }}

        header {{
            background: #000000;
            color: #ffffff;
            padding: clamp(12px, 2.5vw, 20px);
            text-align: center;
            border-bottom: 3px solid #000000;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: clamp(15px, 3vw, 30px);
            flex-wrap: wrap;
        }}

        header h1 {{
            font-size: clamp(1.25rem, 3.5vw, 1.75rem);
            margin: 0;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}

        .filters {{
            display: flex;
            justify-content: center;
            gap: clamp(6px, 1.5vw, 12px);
            flex-wrap: wrap;
        }}

        .filter-badge {{
            background: #ffffff;
            color: #000000;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: clamp(0.65rem, 1.8vw, 0.8rem);
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            border: 2px solid #ffffff;
        }}

        nav {{
            background: #ffffff;
            border-bottom: 2px solid #e0e0e0;
            display: flex;
            justify-content: center;
            gap: 0;
        }}

        nav a {{
            padding: clamp(10px, 2vw, 14px) clamp(20px, 4vw, 30px);
            text-decoration: none;
            color: #666666;
            font-weight: 600;
            font-size: clamp(0.85rem, 2vw, 0.95rem);
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
        }}

        nav a:hover {{
            color: #000000;
            background: #f5f5f5;
        }}

        nav a.active {{
            color: #000000;
            border-bottom-color: #000000;
        }}

        .content {{
            padding: clamp(10px, 3vw, 20px);
        }}

        .section {{
            margin-bottom: 30px;
        }}

        .section-header {{
            background: #000000;
            color: #ffffff;
            padding: 12px 16px;
            font-weight: 700;
            font-size: clamp(0.9rem, 2vw, 1rem);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-radius: 8px 8px 0 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-header.playoffs {{
            background: #006400;
        }}

        .section-header.playins {{
            background: #8B4513;
        }}

        .section-subheader {{
            background: #333333;
            color: #ffffff;
            padding: 8px 16px;
            font-weight: 600;
            font-size: clamp(0.8rem, 1.8vw, 0.9rem);
        }}

        .badge {{
            background: #ffffff;
            color: #000000;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
        }}

        .section-header.playoffs .badge {{
            color: #006400;
        }}

        .section-header.playins .badge {{
            color: #8B4513;
        }}

{page_common.NOTICE_CSS}
        .table-wrapper {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-top: none;
            border-radius: 0 0 8px 8px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: #ffffff;
        }}

        th {{
            padding: 10px 12px;
            text-align: left;
            font-weight: 700;
            font-size: clamp(0.7rem, 1.8vw, 0.8rem);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
            background: #f5f5f5;
            border-bottom: 2px solid #e0e0e0;
        }}

        th:first-child {{
            width: 50px;
            text-align: center;
        }}

        th.stat {{
            text-align: right;
        }}

        tbody tr {{
            border-bottom: 1px solid #e0e0e0;
            transition: all 0.15s ease;
            background: #ffffff;
        }}

        tbody tr:hover {{
            background: #f9f9f9;
        }}

        tbody tr.highlight {{
            background: #f0f0f0;
            border-left: 4px solid #000000;
            border-right: 4px solid #000000;
        }}

        tbody tr.highlight:hover {{
            background: #e8e8e8;
        }}

        tbody tr.highlight td {{
            font-weight: 600;
        }}

        tbody tr:last-child {{
            border-bottom: none;
        }}

        td {{
            padding: 10px 12px;
            color: #333333;
            font-size: clamp(0.85rem, 2vw, 0.95rem);
        }}

        td:first-child {{
            font-weight: 700;
            color: #000000;
            text-align: center;
            font-size: clamp(1rem, 2.2vw, 1.1rem);
        }}

        .team-name {{
            font-weight: 500;
            color: #000000;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .team-logo {{
            width: 28px;
            height: 28px;
            object-fit: contain;
            flex-shrink: 0;
        }}

        .stat {{
            text-align: right;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }}

        .info-box {{
            background: #f9f9f9;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}

        .info-box h3 {{
            font-size: 0.9rem;
            margin-bottom: 8px;
            color: #333333;
        }}

        .info-box p {{
            font-size: 0.85rem;
            color: #666666;
            line-height: 1.5;
        }}

        .pool-label {{
            background: #666666;
            color: #ffffff;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.7rem;
            font-weight: 700;
            margin-left: 10px;
        }}

        footer {{
            text-align: center;
            padding: clamp(15px, 3vw, 25px);
            background: #f5f5f5;
            color: #666666;
            font-size: clamp(0.75rem, 2vw, 0.85rem);
            border-top: 1px solid #e0e0e0;
        }}

        footer a {{
            color: #000000;
            text-decoration: none;
            font-weight: 600;
        }}

        footer a:hover {{
            text-decoration: underline;
        }}

        /* Mobile optimizations */
        @media (max-width: 768px) {{
            .content {{
                padding: 8px;
            }}

            .section {{
                margin-bottom: 15px;
            }}

            .table-wrapper {{
                margin: 0 -8px;
                border-radius: 0;
                border-left: none;
                border-right: none;
            }}

            .section-header {{
                margin: 0 -8px;
                border-radius: 0;
                padding: 10px 12px;
                font-size: 0.8rem;
            }}

            .section-subheader {{
                margin: 0 -8px;
                padding: 6px 12px;
                font-size: 0.75rem;
            }}

            .pool-label {{
                font-size: 0.6rem;
                padding: 2px 6px;
            }}

            .info-box {{
                padding: 10px;
                margin-bottom: 15px;
                font-size: 0.8rem;
            }}

            .info-box h3 {{
                font-size: 0.8rem;
            }}

            .info-box p {{
                font-size: 0.75rem;
            }}

            th, td {{
                padding: 6px 8px;
            }}

            th {{
                font-size: 0.65rem;
            }}

            td {{
                font-size: 0.8rem;
            }}

            td:first-child {{
                font-size: 0.85rem;
            }}

            .team-logo {{
                width: 22px;
                height: 22px;
            }}

            .team-name {{
                gap: 6px;
            }}

            /* Hide WIN% column on tablet */
            th:nth-child(6),
            td:nth-child(6) {{
                display: none;
            }}
        }}

        @media (max-width: 480px) {{
            header {{
                gap: 6px;
                padding: 8px 10px;
            }}

            header h1 {{
                font-size: 0.95rem;
            }}

            .filter-badge {{
                font-size: 0.55rem;
                padding: 3px 6px;
            }}

            nav a {{
                padding: 8px 12px;
                font-size: 0.8rem;
            }}

            .content {{
                padding: 6px;
            }}

            .section {{
                margin-bottom: 12px;
            }}

            .table-wrapper {{
                margin: 0 -6px;
            }}

            .section-header {{
                margin: 0 -6px;
                padding: 8px 10px;
                font-size: 0.75rem;
            }}

            .section-header .badge {{
                font-size: 0.6rem;
                padding: 3px 6px;
            }}

            .section-subheader {{
                margin: 0 -6px;
                padding: 5px 10px;
                font-size: 0.7rem;
            }}

            .info-box {{
                padding: 8px;
                margin-bottom: 12px;
            }}

            .info-box h3 {{
                font-size: 0.75rem;
                margin-bottom: 4px;
            }}

            .info-box p {{
                font-size: 0.7rem;
                line-height: 1.4;
            }}

            th, td {{
                padding: 5px 6px;
            }}

            th {{
                font-size: 0.6rem;
                letter-spacing: 0;
            }}

            td {{
                font-size: 0.75rem;
            }}

            td:first-child {{
                font-size: 0.8rem;
                width: 28px;
            }}

            th:first-child {{
                width: 28px;
            }}

            .team-logo {{
                width: 18px;
                height: 18px;
            }}

            .team-name {{
                gap: 5px;
                font-size: 0.75rem;
            }}

            /* Hide GP and WIN% columns on small mobile */
            th:nth-child(3),
            td:nth-child(3),
            th:nth-child(6),
            td:nth-child(6) {{
                display: none;
            }}

            footer {{
                padding: 12px;
                font-size: 0.7rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{config.SITE_TITLE.upper()}</h1>
            <div class="filters">
                <div class="filter-badge">PLAYOFFS</div>
                <div class="filter-badge">{page_common.region_badge(filters)}</div>
                <div class="filter-badge">{page_common.season_badge(filters)}</div>
            </div>
        </header>

        <nav>
            <a href="index.html">Standings</a>
            <a href="schedule.html">Schedule</a>
            <a href="playoffs.html" class="active">Playoffs</a>
        </nav>

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

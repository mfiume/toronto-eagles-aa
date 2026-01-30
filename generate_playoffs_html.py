#!/usr/bin/env python3
"""
Generate HTML page showing playoff picture based on current standings.
U10 AA West format:
- Top 6 teams go directly to First Round (Playoffs)
- 7th-14th place go to Preliminary Round (Play-ins)
  - Pool A: 7th, 10th, 11th, 14th place
  - Pool B: 8th, 9th, 12th, 13th place
"""

import json
from datetime import datetime, timedelta


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

    # Format timestamp
    try:
        dt_scraped = datetime.fromisoformat(timestamp)
        dt_toronto = dt_scraped - timedelta(hours=5)  # EST offset
        now_utc = datetime.utcnow()
        now_toronto = now_utc - timedelta(hours=5)
        time_diff = now_toronto - dt_toronto

        if time_diff.total_seconds() < 60:
            relative_time = "just now"
        elif time_diff.total_seconds() < 3600:
            minutes = int(time_diff.total_seconds() / 60)
            relative_time = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif time_diff.total_seconds() < 86400:
            hours = int(time_diff.total_seconds() / 3600)
            relative_time = f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(time_diff.total_seconds() / 86400)
            relative_time = f"{days} day{'s' if days != 1 else ''} ago"

        formatted_time = f"{relative_time} ({dt_toronto.strftime('%b %d, %I:%M %p')} ET)"
    except Exception:
        formatted_time = timestamp

    # Categorize teams based on current standings
    # Direct to playoffs: 1st-6th
    # Play-ins Pool A: 7th, 10th, 11th, 14th
    # Play-ins Pool B: 8th, 9th, 12th, 13th
    playoffs_direct = []
    playins_pool_a = []
    playins_pool_b = []

    pool_a_positions = {7, 10, 11, 14}
    pool_b_positions = {8, 9, 12, 13}

    for team in standings:
        pos = team.get("Position", 0)
        if pos <= 6:
            playoffs_direct.append(team)
        elif pos in pool_a_positions:
            playins_pool_a.append(team)
        elif pos in pool_b_positions:
            playins_pool_b.append(team)

    # Sort play-in pools by position
    playins_pool_a.sort(key=lambda x: x.get("Position", 0))
    playins_pool_b.sort(key=lambda x: x.get("Position", 0))

    # Start building HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Toronto Eagles U10 AA - Playoffs</title>
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
                padding: 10px;
            }}

            .section {{
                margin-bottom: 20px;
            }}

            .table-wrapper {{
                margin: 0 -10px;
                border-radius: 0;
                border-left: none;
                border-right: none;
            }}

            .section-header {{
                margin: 0 -10px;
                border-radius: 0;
            }}

            th, td {{
                padding: 8px 10px;
            }}
        }}

        @media (max-width: 480px) {{
            header {{
                gap: 8px;
                padding: 10px 12px;
            }}

            header h1 {{
                font-size: 1rem;
            }}

            .filter-badge {{
                font-size: 0.6rem;
                padding: 4px 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TORONTO EAGLES U10 AA</h1>
            <div class="filters">
                <div class="filter-badge">PLAYOFFS</div>
                <div class="filter-badge">{filters.get('region', 'N/A')} REGION</div>
                <div class="filter-badge">{filters.get('season', 'N/A')}</div>
            </div>
        </header>

        <nav>
            <a href="index.html">Standings</a>
            <a href="schedule.html">Schedule</a>
            <a href="playoffs.html" class="active">Playoffs</a>
        </nav>

        <div class="content">
            <div class="info-box">
                <h3>U10 AA West Playoff Format</h3>
                <p><strong>First Round (Playoffs):</strong> Top 6 teams advance directly to the First Round where they play 7 games in a round robin. Top 6 + 2 play-in winners advance to the Second Round.</p>
                <p style="margin-top: 8px;"><strong>Preliminary Round (Play-ins):</strong> Teams 7th-14th are split into two pools. Each pool plays 3 games, and the top team from each pool advances to join the First Round.</p>
            </div>
"""

    # Direct to Playoffs section
    html += """
            <div class="section">
                <div class="section-header playoffs">
                    First Round (Direct to Playoffs)
                    <span class="badge">TOP 6</span>
                </div>
                <div class="table-wrapper">
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

    for team in playoffs_direct:
        is_eagles = team.get('Team', '').lower() == 'toronto eagles'
        row_class = ' class="highlight"' if is_eagles else ''
        logo_url = team.get('Logo', '')
        html += f"""                            <tr{row_class}>
                                <td>{team.get('Position', '')}</td>
                                <td class="team-name">
                                    <img src="{logo_url}" alt="" class="team-logo" onerror="this.style.display='none'">
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
            </div>
"""

    # Play-ins section
    html += """
            <div class="section">
                <div class="section-header playins">
                    Preliminary Round (Play-ins)
                    <span class="badge">7TH - 14TH</span>
                </div>
"""

    # Pool A
    html += """
                <div class="section-subheader">Pool A <span class="pool-label">7th, 10th, 11th, 14th</span></div>
                <div class="table-wrapper" style="border-radius: 0;">
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

    for team in playins_pool_a:
        is_eagles = team.get('Team', '').lower() == 'toronto eagles'
        row_class = ' class="highlight"' if is_eagles else ''
        logo_url = team.get('Logo', '')
        html += f"""                            <tr{row_class}>
                                <td>{team.get('Position', '')}</td>
                                <td class="team-name">
                                    <img src="{logo_url}" alt="" class="team-logo" onerror="this.style.display='none'">
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

    # Pool B
    html += """
                <div class="section-subheader">Pool B <span class="pool-label">8th, 9th, 12th, 13th</span></div>
                <div class="table-wrapper" style="border-radius: 0 0 8px 8px;">
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

    for team in playins_pool_b:
        is_eagles = team.get('Team', '').lower() == 'toronto eagles'
        row_class = ' class="highlight"' if is_eagles else ''
        logo_url = team.get('Logo', '')
        html += f"""                            <tr{row_class}>
                                <td>{team.get('Position', '')}</td>
                                <td class="team-name">
                                    <img src="{logo_url}" alt="" class="team-logo" onerror="this.style.display='none'">
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
            </div>
"""

    # Footer
    html += f"""        </div>

        <footer>
            <p>Based on current standings as of: {formatted_time}</p>
            <p>Playoff seeding updates nightly at 2:00 AM ET</p>
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

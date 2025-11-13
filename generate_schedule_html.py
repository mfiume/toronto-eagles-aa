#!/usr/bin/env python3
"""
Generate HTML page from scraped schedule data
"""

import json
from datetime import datetime, timedelta


def generate_html():
    """Generate HTML page from schedule.json"""

    # Load schedule data
    with open('schedule.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    schedule = data.get('schedule', [])
    timestamp = data.get('timestamp', '')
    filters = data.get('filters', {})
    error = data.get('error')

    # Format timestamp (same as standings)
    try:
        dt_scraped = datetime.fromisoformat(timestamp)
        dt_toronto = dt_scraped - timedelta(hours=5)  # EST offset

        # Get current Toronto time for comparison
        now_utc = datetime.utcnow()
        now_toronto = now_utc - timedelta(hours=5)

        # Calculate relative time
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
    except Exception as e:
        formatted_time = timestamp

    # Start building HTML (EXACT copy of standings structure)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Toronto Eagles U10 AA - Schedule</title>
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

        .last-updated {{
            text-align: center;
            padding: 12px;
            background: #f9f9f9;
            color: #666666;
            font-size: clamp(0.75rem, 2vw, 0.85rem);
            border-bottom: 1px solid #e0e0e0;
        }}

        .content {{
            padding: clamp(10px, 3vw, 20px);
        }}

        .error {{
            background: #fff5f5;
            border: 2px solid #ff0000;
            color: #cc0000;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin: 20px;
        }}

        .table-wrapper {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            background: #ffffff;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: #ffffff;
            min-width: 800px;
        }}

        thead {{
            background: #000000;
            color: #ffffff;
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        th {{
            padding: 8px 12px;
            text-align: right;
            font-weight: 700;
            font-size: clamp(0.7rem, 1.8vw, 0.8rem);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
            border-bottom: 2px solid #000000;
        }}

        th:first-child {{
            text-align: left;
        }}

        th:nth-child(2) {{
            text-align: left;
        }}

        th:nth-child(3) {{
            text-align: left;
        }}

        th:nth-child(5) {{
            text-align: left;
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

        tbody tr.highlight .team-name {{
            color: #000000;
            font-weight: 700;
        }}

        tbody tr:last-child {{
            border-bottom: none;
        }}

        td {{
            padding: 6px 12px;
            color: #333333;
            font-size: clamp(0.8rem, 2vw, 0.9rem);
        }}

        .team-name {{
            font-weight: 400;
            color: #000000;
            white-space: nowrap;
            text-align: left;
        }}

        .stat {{
            text-align: right;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
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
            body {{
                padding: 0;
            }}

            header {{
                padding: 12px 15px;
                gap: 12px;
            }}

            header h1 {{
                font-size: 1.1rem;
            }}

            .filter-badge {{
                font-size: 0.65rem;
                padding: 5px 10px;
            }}

            .content {{
                padding: 10px;
            }}

            .table-wrapper {{
                margin: 0 -10px;
                border-radius: 0;
                border-left: none;
                border-right: none;
            }}

            table {{
                min-width: 700px;
            }}

            th, td {{
                padding: 6px 8px;
            }}

            th {{
                font-size: 0.7rem;
            }}

            td {{
                font-size: 0.8rem;
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

            table {{
                min-width: 650px;
            }}

            th, td {{
                padding: 5px 6px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TORONTO EAGLES U10 AA</h1>
            <div class="filters">
                <div class="filter-badge">SCHEDULE</div>
                <div class="filter-badge">{filters.get('division', 'N/A')}</div>
                <div class="filter-badge">{filters.get('category', 'N/A')}</div>
            </div>
        </header>

        <nav>
            <a href="index.html">Standings</a>
            <a href="schedule.html" class="active">Schedule</a>
        </nav>

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
        html += """
            <div class="error">
                <h2>No Schedule Data Available</h2>
                <p>No games found.</p>
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
                            <th>Score</th>
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

            # Check if Toronto Eagles are playing
            is_eagles = 'toronto eagles' in away.lower() or 'toronto eagles' in home.lower()
            row_class = ' class="highlight"' if is_eagles else ''

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

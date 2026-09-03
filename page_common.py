#!/usr/bin/env python3
"""
Pieces shared by the three page generators: the "last updated" line, the
filter badges in the header, and the styling for a neutral notice box.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import config

TORONTO = ZoneInfo("America/Toronto")

# A neutral counterpart to .error, for states that are correct rather than
# broken: a season that has not started, a playoff format not yet published.
def format_timestamp(timestamp):
    """
    Render a scrape timestamp as "2 hours ago (Sep 03, 12:56 PM ET)".

    Timestamps written by the scrapers carry an explicit UTC offset. Older ones
    are naive UTC, from when the scrapers ran on GitHub Actions and recorded
    local server time, so treat a naive value as UTC.
    """
    try:
        scraped = datetime.fromisoformat(timestamp)
    except (TypeError, ValueError):
        return timestamp

    if scraped.tzinfo is None:
        scraped = scraped.replace(tzinfo=timezone.utc)

    local = scraped.astimezone(TORONTO)
    elapsed = datetime.now(timezone.utc) - scraped

    seconds = elapsed.total_seconds()
    if seconds < 60:
        relative = "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        relative = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        relative = f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        relative = f"{days} day{'s' if days != 1 else ''} ago"

    return f"{relative} ({local.strftime('%b %d, %I:%M %p')} ET)"


def season_not_started_notice(kind):
    """
    Notice for a division with no standings posted yet.

    `kind` names what the page would otherwise show, e.g. "standings".
    """
    return f"""
            <div class="notice">
                <h2>No {kind} yet for {config.SEASON}</h2>
                <p>The GTHL has not posted {config.DIVISION} {config.CATEGORY}
                {kind} for the {config.SEASON} season. This page fills in once
                games have been played. The schedule is up to date in the
                meantime.</p>
            </div>
"""


# --- Masthead ---------------------------------------------------------------
# The crest is the club's own vector artwork, recoloured white for the red bar.
# Both SVGs are one path set with a single fill, so a second colourway is a
# find-and-replace rather than a new export.

FONT_LINK = """    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&display=swap" rel="stylesheet">"""

_MASTHEAD_CSS = """
        .masthead {
            background: var(--brand);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: clamp(12px, 2.4vw, 20px) clamp(14px, 3vw, 28px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.16);
        }

        .masthead-brand {
            display: flex;
            align-items: center;
            gap: clamp(10px, 1.8vw, 18px);
            text-decoration: none;
            color: inherit;
            min-width: 0;
        }

        .masthead-crest {
            height: clamp(46px, 7.6vw, 70px);
            width: auto;
            flex-shrink: 0;
            display: block;
        }

        .masthead-wordmark {
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 700;
            font-size: clamp(1.15rem, 4.2vw, 2.05rem);
            letter-spacing: 0.015em;
            text-transform: uppercase;
            line-height: 1;
            white-space: nowrap;
        }

        .masthead-meta {
            text-align: right;
            flex-shrink: 0;
            line-height: 1.25;
        }

        .masthead-meta-main {
            display: block;
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 600;
            font-size: clamp(0.72rem, 1.9vw, 0.95rem);
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }

        .masthead-meta-sub {
            display: block;
            font-size: clamp(0.62rem, 1.6vw, 0.78rem);
            letter-spacing: 0.06em;
            color: rgba(255, 255, 255, 0.72);
        }

        .mastnav {
            background: var(--brand-dark);
            display: flex;
            align-items: stretch;
            gap: clamp(2px, 1vw, 10px);
            padding: 0 clamp(8px, 2.4vw, 22px);
            overflow-x: auto;
            scrollbar-width: none;
        }

        .mastnav::-webkit-scrollbar {
            display: none;
        }

        .mastnav a {
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 500;
            font-size: clamp(0.78rem, 2vw, 0.92rem);
            letter-spacing: 0.085em;
            text-transform: uppercase;
            text-decoration: none;
            color: rgba(255, 255, 255, 0.68);
            padding: clamp(11px, 1.9vw, 15px) clamp(12px, 2.2vw, 20px);
            border-bottom: 3px solid transparent;
            white-space: nowrap;
            transition: color 0.15s ease, border-color 0.15s ease;
        }

        .mastnav a:hover {
            color: #ffffff;
        }

        .mastnav a.active {
            color: #ffffff;
            border-bottom-color: #ffffff;
        }

        @media (max-width: 380px) {
            .masthead {
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }

            .masthead-meta {
                text-align: left;
            }
        }
"""

NAV_PAGES = [
    ("index.html", "Standings"),
    ("schedule.html", "Schedule"),
    ("playoffs.html", "Playoffs"),
]


def masthead(active_page, meta_main, meta_sub):
    """
    The red crest bar and the tab bar beneath it, shared by all three pages.

    `active_page` is the filename of the page being generated, so it can mark
    its own tab. `meta_main` and `meta_sub` are the two right-hand lines, which
    say what the page is actually showing.
    """
    html = f"""        <header class="masthead">
            <a class="masthead-brand" href="index.html">
                <img class="masthead-crest" src="assets/eagles-crest-white.svg"
                     alt="{config.TEAM_NAME} crest" width="450" height="567">
                <span class="masthead-wordmark">{config.TEAM_NAME}</span>
            </a>
            <div class="masthead-meta">
                <span class="masthead-meta-main">{meta_main}</span>
                <span class="masthead-meta-sub">{meta_sub}</span>
            </div>
        </header>

        <nav class="mastnav">
"""
    for href, label in NAV_PAGES:
        active = ' class="active"' if href == active_page else ""
        html += f'            <a href="{href}"{active}>{label}</a>\n'
    html += "        </nav>\n"
    return html


def division_label():
    """e.g. 'U11 AA West' - what division this hub covers."""
    return f"{config.DIVISION} {config.CATEGORY} {config.REGION}"


def season_label():
    """e.g. '2026-27 Season' - the season spelled out for the masthead."""
    start, end = config.SEASON.split("-")
    return f"20{start}-{end} Season"


# --- Stylesheet -------------------------------------------------------------
# One stylesheet for all three pages. Each generator used to carry its own
# near-identical copy, which is how the schedule's column headers drifted out
# of alignment with their own cells.
#
# Alignment is driven by the cell classes the generators already emit, not by
# nth-child position: everything is left aligned, and `.stat` is right aligned
# on both the header and the body cell, so a column cannot line up one way in
# the head and another in the body.

_BASE_CSS = """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            color: #111111;
        }

        .container {
            max-width: 100%;
            margin: 0 auto;
            background: #ffffff;
        }

        .content {
            padding: clamp(10px, 3vw, 20px);
        }
"""

_TABLE_CSS = """
        .table-wrapper {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            background: #ffffff;
            border-radius: 8px;
            border: 1px solid #e3e3e3;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: #ffffff;
            min-width: 800px;
        }

        thead {
            background: #14161a;
            color: #ffffff;
            position: sticky;
            top: 0;
            z-index: 10;
        }

        th {
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 500;
            font-size: clamp(0.72rem, 1.8vw, 0.82rem);
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.82);
            padding: 10px 12px;
            text-align: left;
            white-space: nowrap;
            border-bottom: 3px solid var(--crest);
        }

        tbody tr {
            border-bottom: 1px solid #ececec;
            background: #ffffff;
            transition: background 0.15s ease;
        }

        tbody tr:last-child {
            border-bottom: none;
        }

        tbody tr:hover {
            background: #fafafa;
        }

        td {
            padding: 9px 12px;
            text-align: left;
            color: #333333;
            font-size: clamp(0.8rem, 2vw, 0.9rem);
        }

        /* Our own row, tied to the crest rather than to a grey box. */
        tbody tr.highlight {
            background: #fdf4f5;
            box-shadow: inset 4px 0 0 var(--crest);
        }

        tbody tr.highlight:hover {
            background: #fbebed;
        }

        tbody tr.highlight td {
            font-weight: 600;
            color: #1a1a1a;
        }

        tbody tr.highlight .team-name {
            color: var(--brand);
            font-weight: 700;
        }

        .team-name {
            color: #111111;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .team-logo {
            width: 24px;
            height: 24px;
            object-fit: contain;
            flex-shrink: 0;
        }

        /* Numbers line up on the right, in both the header and the body. */
        th.stat,
        td.stat {
            text-align: right;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }

        .rank {
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 600;
            color: #111111;
            font-size: clamp(0.9rem, 2.2vw, 1rem);
            width: 56px;
        }

        .positive {
            color: #0a7a33;
            font-weight: 600;
        }

        .negative {
            color: var(--brand);
            font-weight: 600;
        }
"""

_CHROME_CSS = """
        .notice {
            background: #fafafa;
            border: 1px solid #e3e3e3;
            border-top: 3px solid var(--crest);
            padding: 26px 20px;
            border-radius: 8px;
            text-align: center;
            margin: 20px auto;
            max-width: 720px;
        }

        .notice h2 {
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 600;
            font-size: clamp(0.95rem, 2.4vw, 1.1rem);
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .notice p {
            font-size: 0.85rem;
            color: #666666;
            line-height: 1.55;
        }

        .error {
            background: #fff5f5;
            border: 1px solid #f0c2c5;
            border-top: 3px solid var(--brand);
            color: #8f1119;
            padding: 24px 20px;
            border-radius: 8px;
            text-align: center;
            margin: 20px auto;
            max-width: 720px;
        }

        footer {
            text-align: center;
            padding: clamp(15px, 3vw, 25px);
            background: #f5f5f5;
            color: #767676;
            font-size: clamp(0.75rem, 2vw, 0.82rem);
            border-top: 1px solid #e3e3e3;
        }
"""

_RESPONSIVE_CSS = """
        @media (max-width: 768px) {
            .content {
                padding: 10px;
            }

            .table-wrapper {
                margin: 0 -10px;
                border-radius: 0;
                border-left: none;
                border-right: none;
            }

            table {
                min-width: 700px;
            }

            th, td {
                padding: 7px 8px;
            }

            td {
                font-size: 0.8rem;
            }
        }

        @media (max-width: 480px) {
            table {
                min-width: 650px;
            }

            th, td {
                padding: 6px 6px;
            }
        }
"""

# Brand colours live on :root so the table, the notices and the masthead all
# read from the same two values.
_TOKENS_CSS = """
        :root {
            --brand: #c41520;
            --brand-dark: #a5111a;
            --crest: #ed1c24;
        }
"""

PAGE_CSS = (_TOKENS_CSS + _BASE_CSS + _MASTHEAD_CSS + _TABLE_CSS
            + _CHROME_CSS + _RESPONSIVE_CSS)

# Playoff-page extras: the round headers and the format box.
PLAYOFF_CSS = """
        .section {
            margin-bottom: 28px;
        }

        .section-header {
            background: var(--brand);
            color: #ffffff;
            padding: 12px 16px;
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 600;
            font-size: clamp(0.85rem, 2vw, 0.98rem);
            text-transform: uppercase;
            letter-spacing: 0.07em;
            border-radius: 8px 8px 0 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .section-header.playins {
            background: #3f454d;
        }

        .badge {
            background: #ffffff;
            color: var(--brand);
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.05em;
        }

        .section-header.playins .badge {
            color: #3f454d;
        }

        .section-subheader {
            background: #22262b;
            color: #ffffff;
            padding: 9px 16px;
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 500;
            font-size: clamp(0.78rem, 1.8vw, 0.88rem);
            letter-spacing: 0.06em;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .pool-label {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-weight: 400;
            letter-spacing: 0;
            text-transform: none;
            color: rgba(255, 255, 255, 0.62);
            font-size: 0.76rem;
        }

        .section .table-wrapper {
            border-radius: 0 0 8px 8px;
            border-top: none;
        }

        .info-box {
            background: #fafafa;
            border: 1px solid #e3e3e3;
            border-left: 4px solid var(--crest);
            border-radius: 6px;
            padding: 16px 18px;
            margin-bottom: 26px;
        }

        .info-box h3 {
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .info-box p {
            font-size: 0.85rem;
            color: #555555;
            line-height: 1.55;
            margin-top: 6px;
        }
"""

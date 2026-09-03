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
NOTICE_CSS = """
        .notice {
            background: #fafafa;
            border: 1px solid #e0e0e0;
            color: #333333;
            padding: 24px 20px;
            border-radius: 8px;
            text-align: center;
            margin: 20px;
        }

        .notice h2 {
            font-size: 1rem;
            letter-spacing: 0.02em;
            margin-bottom: 8px;
        }

        .notice p {
            font-size: 0.85rem;
            color: #666666;
            line-height: 1.5;
        }
"""


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

BRAND_CSS = """
        .masthead {
            --brand: #c41520;
            --brand-dark: #a5111a;
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
            background: #a5111a;
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

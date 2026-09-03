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


def region_badge(filters):
    """
    The region badge for the standings and playoffs headers.

    The GTHL only offers a region filter once a division has standings groups,
    so before the first games are played the table is the whole division. Say
    which of the two the page is actually showing.
    """
    if filters.get("region_applied"):
        return f"{filters.get('region', config.REGION)} REGION".upper()
    return f"{config.DIVISION} {config.CATEGORY}".upper()


def season_badge(filters):
    """The season the data actually came from."""
    return filters.get("season", config.SEASON)


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

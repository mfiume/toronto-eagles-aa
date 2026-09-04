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
# Every SVG here is one path set with a single fill, so another colourway is a
# find-and-replace on that value rather than a new export.
#
# The masthead shows the bird alone. The full crest carries its own "EAGLES"
# lettering, which turns to mush at 44px and repeats what the wordmark beside
# it already says. assets/ keeps the complete crest either way.

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
            gap: clamp(10px, 2vw, 20px);
            padding: clamp(11px, 2.2vw, 18px) clamp(12px, 3vw, 24px);
        }

        .masthead-brand {
            display: flex;
            align-items: center;
            gap: clamp(9px, 1.6vw, 16px);
            text-decoration: none;
            color: inherit;
            min-width: 0;
        }

        .masthead-crest {
            height: clamp(40px, 10.5vw, 58px);
            width: auto;
            flex-shrink: 0;
            display: block;
        }

        .masthead-wordmark {
            font-family: var(--display);
            font-weight: 700;
            font-size: clamp(1.05rem, 5.2vw, 1.95rem);
            letter-spacing: 0.01em;
            text-transform: uppercase;
            line-height: 1;
            white-space: nowrap;
        }

        .masthead-meta {
            text-align: right;
            flex-shrink: 0;
            line-height: 1.3;
        }

        .masthead-meta-main {
            display: block;
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(0.66rem, 2.1vw, 0.92rem);
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        .masthead-meta-sub {
            display: block;
            font-size: clamp(0.58rem, 1.7vw, 0.76rem);
            letter-spacing: 0.05em;
            color: rgba(255, 255, 255, 0.74);
        }

        .mastnav {
            background: var(--brand-dark);
            display: flex;
            padding: 0 clamp(6px, 2.2vw, 18px);
            overflow-x: auto;
            scrollbar-width: none;
        }

        .mastnav::-webkit-scrollbar {
            display: none;
        }

        .mastnav a {
            font-family: var(--display);
            font-weight: 500;
            font-size: clamp(0.75rem, 2.1vw, 0.9rem);
            letter-spacing: 0.09em;
            text-transform: uppercase;
            text-decoration: none;
            color: rgba(255, 255, 255, 0.66);
            padding: clamp(11px, 1.9vw, 15px) clamp(11px, 2.2vw, 20px);
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
                <img class="masthead-crest" src="assets/eagles-bird-white.svg"
                     alt="" width="369" height="383">
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


def division_label(filters=None):
    """
    What the page is actually showing, e.g. 'U11 AA West'.

    The region is dropped when a standings scrape could not apply the region
    filter, because the table is then the whole division and saying otherwise
    would be wrong. Pass no filters for the schedule, which is always narrowed
    to our own region by roster.
    """
    label = f"{config.DIVISION} {config.CATEGORY}"
    if filters is None or filters.get("region_applied"):
        return f"{label} {config.REGION}"
    return label


def season_label():
    """e.g. '2026-27 Season' - the season spelled out for the masthead."""
    start, end = config.SEASON.split("-")
    return f"20{start}-{end} Season"


# --- Stylesheet -------------------------------------------------------------
# One stylesheet for all three pages. Each generator used to carry its own
# near-identical copy, which is how the schedule's column headers drifted out
# of alignment with their own cells.
#
# Written mobile first. Nothing on any page scrolls sideways on a phone: the
# standings table reveals columns as the screen earns them, and the schedule
# table becomes one card per game below 720px.
#
# Alignment is driven by the cell classes the generators emit, not by nth-child
# position, so a column cannot line up one way in the head and another in the
# body.

_TOKENS_CSS = """
        :root {
            --brand: #c41520;
            --brand-dark: #a5111a;
            --crest: #ed1c24;
            --crest-wash: #fdf3f4;

            --page: #f1f1f3;
            --surface: #ffffff;
            --line: #e6e6e9;
            --line-soft: #f0f0f2;
            --ink: #111214;
            --ink-2: #55585e;
            --ink-3: #86898f;

            --display: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            --body: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                    'Helvetica Neue', Arial, sans-serif;

            --shell: 1180px;
        }
"""

_BASE_CSS = """
        *, *::before, *::after {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            -webkit-text-size-adjust: 100%;
        }

        body {
            font-family: var(--body);
            background: var(--page);
            color: var(--ink);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }

        .container {
            background: var(--surface);
        }

        .content {
            padding: clamp(12px, 2.6vw, 24px) clamp(10px, 2.6vw, 24px)
                     clamp(26px, 5vw, 44px);
        }

        /* The masthead, the tabs, the content and the footer share one measure,
           so they line up on the same edges and stop growing on a wide
           monitor. */
        @media (min-width: 1228px) {
            .masthead,
            .mastnav,
            .content,
            footer {
                padding-left: calc((100% - var(--shell)) / 2);
                padding-right: calc((100% - var(--shell)) / 2);
            }
        }
"""

_TABLE_CSS = """
        .table-wrapper {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 10px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
        }

        thead {
            background: #16181c;
            color: #ffffff;
        }

        th {
            font-family: var(--display);
            font-weight: 500;
            font-size: clamp(0.66rem, 1.7vw, 0.78rem);
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.86);
            padding: 11px 10px;
            text-align: left;
            white-space: nowrap;
            border-bottom: 3px solid var(--crest);
        }

        tbody tr {
            border-top: 1px solid var(--line-soft);
        }

        tbody tr:first-child {
            border-top: none;
        }

        tbody tr:hover {
            background: #fafafb;
        }

        td {
            padding: 11px 10px;
            vertical-align: middle;
            text-align: left;
            color: var(--ink-2);
            font-size: clamp(0.82rem, 2vw, 0.9rem);
        }

        /* The team cell is a normal table cell so it shares the row's vertical
           alignment; the crest and the name are laid out by an inner box. */
        .team-name {
            color: var(--ink);
            font-weight: 500;
        }

        .team-cell {
            display: flex;
            align-items: center;
            gap: 9px;
            min-width: 0;
        }

        .team-cell > span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .team-logo {
            width: 22px;
            height: 22px;
            object-fit: contain;
            flex-shrink: 0;
        }

        /* Our own row, tied to the crest rather than to a grey box. */
        tbody tr.highlight {
            background: var(--crest-wash);
            box-shadow: inset 3px 0 0 var(--crest);
        }

        tbody tr.highlight:hover {
            background: #fbeced;
        }

        tbody tr.highlight td {
            color: var(--ink);
            font-weight: 600;
        }

        tbody tr.highlight .team-name {
            color: var(--brand);
            font-weight: 700;
        }

        tbody tr.highlight .cell-arena,
        tbody tr.highlight .cell-type {
            color: var(--ink-2);
            font-weight: 500;
        }

        /* Numbers line up on the right, in both the header and the body. */
        th.stat,
        td.stat {
            text-align: right;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }

        .rank {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(0.85rem, 2.1vw, 0.98rem);
            width: 1%;
            white-space: nowrap;
            padding-right: 2px;
        }

        td.rank {
            color: var(--ink);
        }

        /* Secondary columns appear only once the screen is wide enough to earn
           them, which is what keeps the standings inside a phone. */
        .col-md,
        .col-lg {
            display: none;
        }

        @media (min-width: 620px) {
            .col-md {
                display: table-cell;
            }
        }

        @media (min-width: 1000px) {
            .col-lg {
                display: table-cell;
            }
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

# The schedule is a table on a laptop and one card per game on a phone, from
# the same markup. Games are grouped under a date heading either way, so the
# date is written once instead of on every row.
_SCHEDULE_CSS = """
        .date-row th {
            background: #f6f6f8;
            color: var(--ink-2);
            border-top: 1px solid var(--line);
            border-bottom: 1px solid var(--line);
            font-size: clamp(0.66rem, 1.8vw, 0.74rem);
            letter-spacing: 0.12em;
            padding: 8px 10px;
        }

        .schedule-table tbody tr:first-child .date-head {
            border-top: none;
        }

        .cell-arena {
            color: var(--ink-3);
            white-space: normal;
        }

        .cell-type {
            color: var(--ink-3);
            font-size: 0.74rem;
            letter-spacing: 0.06em;
        }

        @media (min-width: 720px) {
            .schedule-table .cell-time,
            .schedule-table .cell-away,
            .schedule-table .cell-score,
            .schedule-table .cell-home,
            .schedule-table .cell-type {
                width: 1%;
                white-space: nowrap;
            }

            .schedule-table .cell-score {
                padding-right: 22px;
            }

            .schedule-table .cell-arena {
                width: auto;
            }
        }

        @media (max-width: 719px) {
            .schedule-table,
            .schedule-table tbody,
            .schedule-table tr,
            .schedule-table td,
            .schedule-table th {
                display: block;
            }

            .schedule-table thead {
                display: none;
            }

            .schedule-table .date-row th {
                padding: 9px 13px;
            }

            .schedule-table tr.game {
                display: grid;
                grid-template-columns: 1fr auto;
                grid-template-areas:
                    "time  type"
                    "away  score"
                    "home  score"
                    "arena arena";
                align-items: center;
                column-gap: 12px;
                padding: 11px 13px 12px;
            }

            .schedule-table tr.game td {
                padding: 0;
            }

            .schedule-table .cell-time {
                grid-area: time;
                font-family: var(--display);
                font-weight: 500;
                font-size: 0.76rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--ink-2);
            }

            .schedule-table .cell-type {
                grid-area: type;
                text-align: right;
            }

            .schedule-table .cell-away {
                grid-area: away;
                padding-top: 5px !important;
            }

            .schedule-table .cell-home {
                grid-area: home;
            }

            /* The column headers are gone at this width, so the home side
               has to say so itself. */
            .schedule-table .cell-home::before {
                content: "at ";
                color: var(--ink-3);
                font-weight: 400;
            }

            .schedule-table .cell-away,
            .schedule-table .cell-home {
                font-size: 0.95rem;
                line-height: 1.4;
            }

            .schedule-table .cell-score {
                grid-area: score;
                font-family: var(--display);
                font-weight: 600;
                font-size: 1.15rem;
                color: var(--ink);
                text-align: right;
            }

            .schedule-table .cell-arena {
                grid-area: arena;
                font-size: 0.76rem;
                padding-top: 5px !important;
            }
        }
"""

_CHROME_CSS = """
        .notice,
        .error {
            position: relative;
            overflow: hidden;
            border-radius: 10px;
            text-align: center;
            margin: clamp(14px, 4vw, 28px) auto;
            max-width: 640px;
            padding: clamp(22px, 5vw, 30px) clamp(18px, 5vw, 26px);
        }

        .notice {
            background: #fafafa;
            border: 1px solid var(--line);
        }

        .notice::before,
        .error::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--crest);
        }

        .notice h2,
        .error h2 {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(0.98rem, 3vw, 1.15rem);
            letter-spacing: 0.045em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .notice p,
        .error p {
            font-size: 0.87rem;
            color: var(--ink-2);
            line-height: 1.6;
        }

        .error {
            background: #fff6f6;
            border: 1px solid #f0c2c5;
            color: #8f1119;
        }

        .error::before {
            background: var(--brand);
        }

        .error p {
            color: #8f1119;
        }

        footer {
            text-align: center;
            padding: clamp(18px, 4vw, 28px) clamp(12px, 3vw, 24px);
            background: var(--page);
            color: var(--ink-3);
            font-size: clamp(0.72rem, 2vw, 0.8rem);
            line-height: 1.7;
            border-top: 1px solid var(--line);
        }
"""

_RESPONSIVE_CSS = """
        @media (max-width: 719px) {
            th,
            td {
                padding: 10px 8px;
            }

            .rank {
                padding-left: 10px;
            }
        }

        @media (max-width: 389px) {
            th,
            td {
                padding: 10px 4px;
                font-size: 0.78rem;
            }

            .rank {
                padding-left: 7px;
                padding-right: 0;
            }

            .team-logo {
                display: none;
            }
        }
"""

# --- Sponsor ----------------------------------------------------------------
# The club's sponsor sits at the end of the page, on its own white band between
# the content and the small print. It reads as part of the page rather than as
# an ad: no box, no border around the mark, no dimming, and the logo is shown
# unaltered on white because it is supplied on an opaque white background.

SPONSOR = {
    "name": "Recruit Connect",
    "url": "https://www.recruit-connect.ca/",
    "logo": "assets/recruit-connect.png",
    "logo_width": 540,
    "logo_height": 247,
}

_SPONSOR_CSS = """
        .sponsor {
            background: #ffffff;
            border-top: 1px solid var(--line);
            padding: clamp(24px, 5vw, 36px) 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: clamp(12px, 2vw, 16px);
        }

        .sponsor-label {
            font-family: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            font-weight: 500;
            font-size: 0.68rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: #9b9b9b;
        }

        .sponsor-link {
            display: block;
            line-height: 0;
        }

        .sponsor-logo {
            width: clamp(158px, 42vw, 196px);
            height: auto;
            display: block;
        }
"""


def sponsor_block():
    """The sponsor band, shown at the foot of every page."""
    return f"""        <div class="sponsor">
            <span class="sponsor-label">Team Sponsor</span>
            <a class="sponsor-link" href="{SPONSOR['url']}"
               target="_blank" rel="noopener noreferrer">
                <img class="sponsor-logo" src="{SPONSOR['logo']}"
                     alt="{SPONSOR['name']}"
                     width="{SPONSOR['logo_width']}" height="{SPONSOR['logo_height']}">
            </a>
        </div>
"""


def page_footer(*lines):
    """The sponsor band plus the page's own small print."""
    html = sponsor_block()
    html += "\n        <footer>\n"
    for line in lines:
        html += f"            <p>{line}</p>\n"
    html += "        </footer>\n"
    return html


PAGE_CSS = (_TOKENS_CSS + _BASE_CSS + _MASTHEAD_CSS + _TABLE_CSS
            + _SCHEDULE_CSS + _CHROME_CSS + _SPONSOR_CSS + _RESPONSIVE_CSS)

# Playoff-page extras: the round headers and the format box.
PLAYOFF_CSS = """
        .section {
            margin-bottom: clamp(20px, 4vw, 30px);
        }

        .section-header {
            background: var(--brand);
            color: #ffffff;
            padding: 12px 14px;
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(0.8rem, 2.2vw, 0.96rem);
            text-transform: uppercase;
            letter-spacing: 0.07em;
            line-height: 1.3;
            border-radius: 10px 10px 0 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }

        .section-header.playins {
            background: #3a4048;
        }

        .badge {
            background: #ffffff;
            color: var(--brand);
            padding: 3px 9px;
            border-radius: 3px;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            white-space: nowrap;
            flex-shrink: 0;
        }

        .section-header.playins .badge {
            color: #3a4048;
        }

        .section-subheader {
            background: #22262b;
            color: #ffffff;
            padding: 9px 14px;
            font-family: var(--display);
            font-weight: 500;
            font-size: clamp(0.74rem, 2vw, 0.86rem);
            letter-spacing: 0.06em;
            text-transform: uppercase;
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 4px 9px;
        }

        .pool-label {
            font-family: var(--body);
            font-weight: 400;
            letter-spacing: 0;
            text-transform: none;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.74rem;
        }

        .section .table-wrapper {
            border-radius: 0 0 10px 10px;
            border-top: none;
        }

        .info-box {
            background: #fafafa;
            border: 1px solid var(--line);
            border-left: 3px solid var(--crest);
            border-radius: 8px;
            padding: clamp(14px, 3vw, 18px);
            margin-bottom: clamp(18px, 4vw, 26px);
        }

        .info-box h3 {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(0.85rem, 2.4vw, 0.95rem);
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .info-box p {
            font-size: 0.85rem;
            color: var(--ink-2);
            line-height: 1.6;
            margin-top: 6px;
        }
"""

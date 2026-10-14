#!/usr/bin/env python3
"""
Pieces shared by the three page generators: the "last updated" line, the
filter badges in the header, and the styling for a neutral notice box.
"""

import html
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import config
from season_schedule import slug

TORONTO = ZoneInfo("America/Toronto")

# A neutral counterpart to .error, for states that are correct rather than
# broken: a season that has not started, a playoff format not yet published.
def _parse_timestamp(timestamp):
    """A scrape timestamp as an aware UTC datetime, or None."""
    try:
        scraped = datetime.fromisoformat(timestamp)
    except (TypeError, ValueError):
        return None
    # Timestamps written by the scrapers carry an explicit UTC offset. Older
    # ones are naive UTC, from when the scrapers recorded the GitHub Actions
    # server's own clock, so treat a naive value as UTC.
    return scraped.replace(tzinfo=timezone.utc) if scraped.tzinfo is None else scraped


def relative_time(timestamp):
    """How long ago, e.g. "just now" or "3 hours ago"."""
    scraped = _parse_timestamp(timestamp)
    if scraped is None:
        return timestamp

    seconds = (datetime.now(timezone.utc) - scraped).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds / 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"


def absolute_time(timestamp):
    """The wall-clock time in Toronto, e.g. "Sep 04, 02:18 AM ET"."""
    scraped = _parse_timestamp(timestamp)
    if scraped is None:
        return ""
    return f"{scraped.astimezone(TORONTO).strftime('%b %d, %I:%M %p')} ET"


def machine_time(timestamp):
    """ISO 8601 for the <time datetime> attribute."""
    scraped = _parse_timestamp(timestamp)
    return scraped.isoformat() if scraped else ""


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
# A white bar with a thin red rule along the top. Red is the club's accent, not
# a background: it marks the active tab, our own games and the countdown, and
# nothing else, so it still means something wherever it appears.
#
# The mark is the bird alone, in the crest's own red. The full crest carries its
# own "EAGLES" lettering, which turns to mush at masthead size and repeats the
# wordmark beside it. Every SVG in assets/ is one path set with a single fill,
# so another colourway is a find-and-replace on that value, not a new export.

FONT_LINK = """    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Oswald:wght@500;600;700&display=swap" rel="stylesheet">"""

# The browser-tab and home-screen icons: the bird in club red on white, in the
# crest's own line weight. assets/favicon.svg (tab) and assets/app-icon.svg
# (home screen) differ only in how much of the square the bird fills. The PNGs
# are rendered from those two for browsers that do not take an SVG icon.
# manifest.webmanifest lists the same icons and names the home-screen shortcut
# "Eagles" on iOS and Android.
FAVICON_LINKS = """    <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
    <link rel="icon" href="assets/favicon-32.png" type="image/png" sizes="32x32">
    <link rel="icon" href="assets/icon-192.png" type="image/png" sizes="192x192">
    <link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png">
    <link rel="manifest" href="manifest.webmanifest">
    <meta name="apple-mobile-web-app-title" content="Eagles">"""

_MASTHEAD_CSS = """
        .masthead {
            background: var(--surface);
            color: var(--ink);
            border-top: 3px solid var(--brand);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: clamp(10px, 2vw, 20px);
            padding: clamp(11px, 2.2vw, 16px) clamp(12px, 3vw, 24px);
        }

        .masthead-brand {
            display: flex;
            align-items: center;
            gap: clamp(8px, 1.4vw, 12px);
            text-decoration: none;
            color: inherit;
            min-width: 0;
        }

        .masthead-mark {
            height: clamp(28px, 6vw, 36px);
            width: auto;
            flex-shrink: 0;
        }

        .masthead-wordmark {
            font-family: var(--display);
            font-weight: 700;
            font-size: clamp(1.05rem, 5vw, 1.75rem);
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
            font-size: clamp(0.66rem, 2.1vw, 0.82rem);
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        .masthead-meta-sub {
            display: block;
            font-size: clamp(0.62rem, 1.7vw, 0.74rem);
            color: var(--ink-3);
        }

        @media (max-width: 479px) {
            .masthead-meta-sub {
                display: none;
            }
        }

        .mastnav {
            background: var(--surface);
            border-bottom: 1px solid var(--line);
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
            font-size: clamp(0.75rem, 2.1vw, 0.86rem);
            letter-spacing: 0.08em;
            text-transform: uppercase;
            text-decoration: none;
            color: var(--ink-2);
            padding: clamp(11px, 1.9vw, 14px) clamp(11px, 2.2vw, 16px);
            border-bottom: 3px solid transparent;
            white-space: nowrap;
            transition: color 0.15s ease, border-color 0.15s ease;
        }

        .mastnav a:hover {
            color: var(--ink);
        }

        .mastnav a.active {
            color: var(--brand);
            border-bottom-color: var(--brand);
        }

        /* Team Login / Log out sits at the far right of the tabs, quieter than a
           tab: no underline state, just the label. */
        .mastnav a.mastnav-auth {
            margin-left: auto;
            color: var(--ink-2);
            text-transform: none;
            letter-spacing: 0.02em;
            font-family: var(--body);
            font-weight: 600;
        }

        .mastnav a.mastnav-auth:hover {
            color: var(--ink);
        }
"""

# Every page the hub can show. config.HIDDEN_PAGES decides which of them are
# actually linked, so a page can be built and waiting without being offered.
NAV_PAGES = [
    ("index.html", "Standings"),
    ("schedule.html", "Schedule"),
    ("playoffs.html", "Playoffs"),
]


def masthead(active_page, meta_main, meta_sub):
    """
    The masthead and the tab bar beneath it, shared by every page.

    `active_page` is the filename of the page being generated, so it can mark
    its own tab. `meta_main` and `meta_sub` are the two right-hand lines, which
    say what the page is actually showing.
    """
    html = f"""        <header class="masthead">
            <a class="masthead-brand" href="index.html">
                <img class="masthead-mark" src="assets/eagles-bird-red.svg" alt=""
                     width="369" height="383">
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
        # A hidden page still shows its own tab if that is where you are, so
        # arriving by direct link does not leave the nav lying about it.
        if href in config.HIDDEN_PAGES and href != active_page:
            continue
        active = ' class="active"' if href == active_page else ""
        html += f'            <a href="{href}"{active}>{label}</a>\n'
    if auth_enabled():
        html += AUTH_LINK
    html += "        </nav>\n"
    return html + sponsor_strip()


def auth_enabled():
    """Whether the site offers the family log-in: the team password is set."""
    return bool(os.environ.get("TEAM_EVENTS_PASSWORD"))


# Family log-in, at the right end of the tab bar on every page. Logging in
# means entering the team password, which unlocks the team events on the
# schedule page (see team_crypto.py); the phone remembers it until Log out.
# The link starts as "Team Login" and a few lines of script set it from what the
# phone remembers. On the schedule page SCHEDULE_JS takes it over to open the
# log-in box in place; elsewhere it goes to the schedule page and opens it.
AUTH_LINK = """            <a class="mastnav-auth" href="schedule.html#login" data-auth-link>Team Login</a>
            <script>
            (function () {
              var link = document.currentScript.previousElementSibling;
              var saved = null;
              try { saved = localStorage.getItem('eagles-team-password'); } catch (e) {}
              if (!saved) return;
              link.textContent = 'Log out';
              link.dataset.loggedIn = '1';
              link.addEventListener('click', function (event) {
                // The schedule page logs out itself (it also has to put the
                // public schedule back). This runs before the rest of the page
                // has loaded, so which page it is can only be told on click.
                if (document.querySelector('[data-schedule-block]')) return;
                event.preventDefault();
                try { localStorage.removeItem('eagles-team-password'); } catch (e) {}
                link.textContent = 'Team Login';
                delete link.dataset.loggedIn;
              }, { once: true });
            })();
            </script>
"""


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


# --- Team logos -------------------------------------------------------------
# fetch_logos.py caches each club's logo as assets/logos/<team-slug>.png.

LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logos")


def win_pct(row):
    """
    A team's win percentage, ties counting half: the GTHL's WIN% when it gives
    one, otherwise worked out from W-L-T. None before a team has played.
    """
    value = str(row.get("WIN%", "")).strip()
    try:
        return float(value)
    except ValueError:
        pass
    try:
        w, l, t = (int(n) for n in str(row.get("W-L-T", "")).split("-"))
    except ValueError:
        return None
    played = w + l + t
    return (w + t / 2) / played if played else None


def rank_standings(standings):
    """
    The standings in our order: points, then win percentage as the tie
    breaker, with Position renumbered to match. A team yet to play ranks above
    one that has only lost; teams level on both keep the GTHL's order.
    """
    def points(row):
        try:
            return int(row.get("PTS") or 0)
        except ValueError:
            return 0

    def key(row):
        pct = win_pct(row)
        return (-points(row), -(0.25 if pct is None and points(row) == 0 else pct or 0),
                row.get("Position", 0))

    ranked = sorted(standings, key=key)
    return [dict(row, Position=n) for n, row in enumerate(ranked, 1)]


def team_logo(team, fallback_url=None):
    """
    A team's logo, served from our own cache.

    Without a cached file this uses `fallback_url` (the GTHL's own copy, which
    the standings scrape records) if there is one, or the team's initials in
    the same footprint, so rows never jump around a missing image.
    """
    filename = f"{slug(team)}.png"
    if os.path.exists(os.path.join(LOGO_DIR, filename)):
        return f'<img class="team-logo" src="assets/logos/{filename}" alt="" loading="lazy">'
    if fallback_url:
        return (f'<img class="team-logo" src="{html.escape(fallback_url)}" alt="" loading="lazy" '
                'onerror="this.style.display=\'none\'">')
    initials = "".join(w[0] for w in team.removeprefix("The ").split())[:3].upper()
    return f'<span class="team-logo team-mono" aria-hidden="true">{html.escape(initials)}</span>'


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

            --surface: #ffffff;
            --wash: #f6f5f7;
            --line: #e6e6e9;
            --line-soft: #f0f0f2;
            --ink: #111214;
            --ink-2: #55585e;
            --ink-3: #86898f;

            --display: 'Oswald', 'Arial Narrow', 'Helvetica Neue', sans-serif;
            --body: 'Barlow', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                    Roboto, 'Helvetica Neue', Arial, sans-serif;

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
            background: var(--surface);
            color: var(--ink);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }

        .container {
            background: var(--surface);
        }

        /* A faint grey behind the content only, so the white tables and game
           cards read as objects on it. The masthead and sponsors stay white. */
        .content {
            background: var(--wash);
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
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        table {
            width: 100%;
            /* Separate, not collapsed: Safari leaves collapsed borders
               behind when a pinned (sticky) cell moves. Each cell draws its
               own lines instead. */
            border-collapse: separate;
            border-spacing: 0;
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

        tbody tr + tr td {
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

        /* Every column shows on every screen; a table wider than the screen
           scrolls sideways, with the rank and the team pinned on the left so
           a row can still be read mid-scroll. */
        th,
        td {
            white-space: nowrap;
        }

        /* Pixels, not ems: the header's smaller type would otherwise pin
           its cells at a different offset from the rows beneath. */
        .table-wrapper .rank {
            position: sticky;
            left: 0;
            z-index: 1;
            box-sizing: border-box;
            width: 40px;
            min-width: 40px;
            max-width: 40px;
            background: var(--surface);
        }

        th.rank {
            background: #16181c;
        }

        .table-wrapper td.team-name,
        .table-wrapper th.team-col {
            position: sticky;
            left: 40px;
            z-index: 1;
            background: var(--surface);
            box-shadow: inset -1px 0 0 var(--line-soft);
        }

        .table-wrapper th.team-col {
            background: #16181c;
            box-shadow: none;
        }

        tbody tr:hover td.rank,
        tbody tr:hover td.team-name {
            background: #fafafb;
        }

        tbody tr.highlight td.rank,
        tbody tr.highlight td.team-name {
            background: var(--crest-wash);
        }

        tbody tr.highlight:hover td.rank,
        tbody tr.highlight:hover td.team-name {
            background: #fbeced;
        }

        /* The red bar on our row belongs to the pinned rank cell. */
        tbody tr.highlight td.rank {
            box-shadow: inset 3px 0 0 var(--crest);
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

# The schedule is a column of game cards, grouped by week, under a card for the
# next Eagles game. Our own games are one line about the opponent; everyone
# else's show both teams. Red marks only our games and the countdown.
_SCHEDULE_CSS = """
        .schedule {
            max-width: 860px;
            margin: 0 auto;
            display: grid;
            gap: 18px;
        }

        /* --- Next game --- */

        .next {
            background: var(--surface);
            border: 1px solid var(--line);
            padding: 14px 18px;
            display: grid;
            gap: 12px;
        }

        .next-top {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.74rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--ink-2);
        }

        .next-when {
            color: var(--brand);
        }

        .face {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
            align-items: center;
            gap: 12px;
        }

        .face-team {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(0.85rem, 2.6vw, 1.05rem);
            line-height: 1.15;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }

        .face-team.home {
            flex-direction: row-reverse;
            text-align: right;
        }

        .face-team .team-logo {
            width: 32px;
            height: 32px;
        }

        .face-role {
            display: block;
            font-family: var(--body);
            font-weight: 500;
            font-size: 0.62rem;
            letter-spacing: 0.12em;
            color: var(--ink-3);
            margin-top: 2px;
        }

        .face-vs {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.8rem;
            color: var(--ink-3);
        }

        .next-foot {
            display: flex;
            flex-wrap: wrap;
            gap: 4px 16px;
            font-size: 0.9rem;
            color: var(--ink-2);
            border-top: 1px solid var(--line);
            padding-top: 10px;
        }

        .next-foot strong {
            color: var(--ink);
            font-weight: 600;
        }

        /* --- Heading and the Eagles / all games toggle --- */

        .sched-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .sched-head h2 {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.82rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--ink-2);
        }

        .sched-filter {
            display: inline-flex;
            border: 1px solid var(--line);
            background: var(--surface);
        }

        .sched-filter-btn {
            appearance: none;
            border: 0;
            background: transparent;
            cursor: pointer;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.74rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-2);
            padding: 8px 14px;
            display: inline-flex;
            align-items: baseline;
            gap: 6px;
            transition: background 0.15s ease, color 0.15s ease;
        }

        .sched-filter-btn:hover {
            color: var(--ink);
        }

        .sched-filter-btn[aria-pressed="true"] {
            background: var(--ink);
            color: #ffffff;
        }

        .sched-filter-btn:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 2px;
        }

        /* The filters hide rows and weeks with the hidden attribute; rows
           and weeks set their own display, so it has to be made to win. */
        .sched-weeks [hidden] {
            display: none !important;
        }

        /* Logged in, Games / Practices / All joins the Eagles / All toggle on
           the heading's line, one at each end. The two toggles say what the
           list is, so the "Schedule" label steps aside to make room. */
        .sched-head.has-type {
            flex-wrap: nowrap;
            gap: 8px;
        }

        .sched-head.has-type h2 {
            position: absolute;
            width: 1px;
            height: 1px;
            overflow: hidden;
            clip: rect(0 0 0 0);
            white-space: nowrap;
        }

        @media (max-width: 519px) {
            .sched-head.has-type .sched-filter-btn {
                padding: 8px 9px;
                gap: 4px;
            }
        }

        .sched-filter-count {
            font-size: 0.68rem;
            opacity: 0.7;
            font-variant-numeric: tabular-nums;
        }

        /* --- Weeks --- */

        .week {
            display: grid;
            gap: 8px;
        }

        .week-head {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 10px;
            padding: 8px 2px 0;
        }

        .week-label {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .week-label.now {
            color: var(--brand);
        }

        .week-count {
            font-size: 0.8rem;
            color: var(--ink-3);
        }

        /* --- One game ---
           Every game is the same compact row: day and time, both teams
           stacked, the rink. Ours differ only by the red bar on the left. */

        .week-games {
            background: var(--surface);
            border: 1px solid var(--line);
        }

        .game {
            display: grid;
            grid-template-columns: 62px minmax(0, 1fr);
            align-items: center;
            gap: 12px;
            padding: 8px 12px;
        }

        .game + .game {
            border-top: 1px solid var(--line);
        }

        .game.is-ours {
            box-shadow: inset 3px 0 0 var(--brand);
        }



        .game-when {
            line-height: 1.15;
        }

        .game-day {
            display: block;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.74rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink);
        }

        .game-time {
            display: block;
            font-family: var(--display);
            font-weight: 500;
            font-size: 0.82rem;
            font-variant-numeric: tabular-nums;
            color: var(--ink-2);
            margin-top: 2px;
            white-space: nowrap;
        }

        /* Names, then the row's icons, then the goals. The two team lines
           and their goals take rows 1 and 2; the icons span both, and
           anything else (a game's label, the drawer) runs full width below. */
        .game-teams {
            display: grid;
            /* The goals column is kept on every row, so play icons line up. */
            grid-template-columns: minmax(0, 1fr) auto 1.8rem;
            row-gap: 3px;
            min-width: 0;
        }

        .game-teams > * {
            grid-column: 1 / -1;
        }

        .game-teams > .r1,
        .game-teams > .r2 {
            grid-column: 1;
        }

        .game-teams > .r1 {
            grid-row: 1;
        }

        .game-teams > .r2 {
            grid-row: 2;
        }

        .game-teams > .game-goals {
            grid-column: 3;
        }

        .game-teams > .game-icons {
            grid-column: 2;
            grid-row: 1 / span 2;
            display: flex;
            align-items: center;
            padding-left: 6px;
        }

        /* Icon links: a 32px target around a small glyph. */
        .icon-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            margin: -6px 0;
            color: var(--ink-3);
        }

        .icon-btn svg {
            width: 13px;
            height: 13px;
            fill: currentColor;
        }

        .icon-btn:hover {
            color: var(--ink);
        }

        .icon-btn:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: -2px;
        }

        /* Rewatch: a grey play icon. Live: the same in red, pulsing, beside
           the LIVE flag in the time's place. */
        .icon-btn.game-watch::before {
            content: none !important;
        }

        .icon-btn.game-watch {
            color: var(--ink-2);
        }

        .icon-btn.game-watch svg {
            width: 14px;
            height: 14px;
        }

        .icon-btn.game-watch.is-live {
            color: var(--brand);
        }

        .icon-btn.game-watch.is-live svg {
            animation: live-pulse 1.6s ease-in-out infinite;
        }

        @media (prefers-reduced-motion: reduce) {
            .icon-btn.game-watch.is-live svg {
                animation: none;
            }
        }

        .game-team {
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
            font-size: 0.92rem;
            line-height: 1.25;
            color: var(--ink);
        }

        .game-team > span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .game-team.us {
            font-weight: 600;
        }

        .game-team .team-logo {
            width: 18px;
            height: 18px;
        }

        .game-rink {
            color: var(--ink-2);
        }

        /* A rink with a known address opens directions. It keeps the quiet
           rink styling and adds a dotted underline and a pin, so it reads as
           tappable without competing with the teams. */
        a.game-rink {
            text-decoration: underline dotted;
            text-underline-offset: 2px;
            text-decoration-color: var(--ink-3);
        }

        a.game-rink::before {
            content: "";
            display: inline-block;
            width: 0.62em;
            height: 0.8em;
            margin-right: 3px;
            vertical-align: -0.05em;
            background: currentColor;
            -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 13'%3E%3Cpath d='M5 0a5 5 0 0 0-5 5c0 3.6 5 8 5 8s5-4.4 5-8a5 5 0 0 0-5-5Zm0 7a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z'/%3E%3C/svg%3E") center / contain no-repeat;
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 13'%3E%3Cpath d='M5 0a5 5 0 0 0-5 5c0 3.6 5 8 5 8s5-4.4 5-8a5 5 0 0 0-5-5Zm0 7a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z'/%3E%3C/svg%3E") center / contain no-repeat;
        }

        a.game-rink:hover {
            color: var(--ink);
        }

        a.game-rink:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 2px;
        }

        /* In the next-game card the rink itself is the directions link. */
        .next-rink {
            color: inherit;
            text-decoration: underline;
            text-underline-offset: 3px;
            text-decoration-color: var(--ink-3);
        }

        .next-rink:hover {
            color: var(--ink);
        }

        .next-rink:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 2px;
        }

        /* --- LiveBarn ---
           The link lives in the row's drawer: nothing before puck drop, a
           red LIVE for the first hour, Rewatch after. While a game is live,
           "LIVE" also stands in for its start time, so it shows unopened. */
        .game-watch {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.7rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-2);
            text-decoration: none;
            white-space: nowrap;
        }

        .game-watch[hidden] {
            display: none;
        }

        .game-watch.is-rewatch::before,
        .game-watch.is-upcoming::before {
            content: "";
            width: 0;
            height: 0;
            border-left: 6px solid currentColor;
            border-top: 4px solid transparent;
            border-bottom: 4px solid transparent;
        }

        .game-watch.is-live {
            color: var(--brand);
        }

        .game-watch.is-live::before {
            content: "";
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: currentColor;
            animation: live-pulse 1.6s ease-in-out infinite;
        }

        @keyframes live-pulse {
            50% {
                opacity: 0.25;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            .game-watch.is-live::before {
                animation: none;
            }
        }

        .game-watch:hover {
            color: var(--ink);
        }

        .game-watch.is-live:hover {
            color: var(--brand-dark);
        }

        .game-watch:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 2px;
        }

        .next-watch {
            margin-left: auto;
        }

        /* --- A played game ---
           "Final" in the time's place, each team's goals at the end of its
           line, the winner bold and the loser quieter. */
        .game-name {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            min-width: 0;
        }

        .game-goals {
            align-self: center;
            font-family: var(--display);
            font-weight: 600;
            font-size: 1rem;
            font-variant-numeric: tabular-nums;
            min-width: 1.4em;
            text-align: right;
        }

        .game-team.won {
            font-weight: 600;
        }

        .game-team.lost {
            color: var(--ink-2);
        }

        .game-goals.won {
            font-weight: 600;
        }

        .game-goals.lost {
            font-weight: 500;
            color: var(--ink-2);
        }

        .game-final {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.7rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--ink-2);
        }

        .game-result {
            display: inline-block;
            margin-left: 6px;
            padding: 1px 5px;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.66rem;
            letter-spacing: 0.06em;
            vertical-align: 1px;
        }

        .result-w {
            background: var(--ink);
            color: #ffffff;
        }

        .result-l {
            color: var(--ink-2);
            box-shadow: inset 0 0 0 1px var(--line);
        }

        .result-t {
            background: #ececf0;
            color: var(--ink);
        }


        /* --- Team events (unlocked) ---
           Same row as a game. A team event has a grey bar where our games
           have red, and one line about what it is. */
        .game-extra {
            font-size: 0.78rem;
            line-height: 1.3;
            color: var(--ink-2);
            margin-top: 1px;
        }

        .game.team-event.is-ours {
            box-shadow: inset 3px 0 0 #cfcdd3;
        }

        .game.team-event.kind-tournament {
            box-shadow: inset 3px 0 0 var(--ink);
            background: #fafafb;
        }

        .event-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            line-height: 1.25;
            color: var(--ink);
            min-width: 0;
        }

        .event-title > span:last-child {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .event-tag {
            flex-shrink: 0;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.6rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            padding: 2px 5px;
            background: var(--ink);
            color: #ffffff;
        }

        /* Arrival time and what to wear stay folded away until the row is
           tapped; the next-game card shows them open. There is no marker on
           purpose: it is a quiet extra, not something to learn. */
        .game.has-details {
            cursor: pointer;
        }

        .game.has-details .game-details {
            display: none;
        }

        .game.has-details.is-open .game-details {
            display: flex;
        }

        .game-details {
            flex-wrap: wrap;
            align-items: center;
            gap: 4px 14px;
            margin-top: 6px;
            font-size: 0.8rem;
        }

        /* The live flag in the time's place. */
        .game-live {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            margin-top: 2px;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.76rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--brand);
        }

        .game-live::before {
            content: "";
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: currentColor;
            animation: live-pulse 1.6s ease-in-out infinite;
        }

        .game-live[hidden] {
            display: none;
        }

        .game.is-live .game-time {
            display: none;
        }

        @media (prefers-reduced-motion: reduce) {
            .game-live::before {
                animation: none;
            }
        }

        .game.has-details:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: -2px;
        }

        .next-extra .game-extra {
            margin-top: 0;
            font-size: 0.84rem;
        }

        /* --- Family log-in box ---
           A plain modal: title, one line of explanation, the password, and
           Log in / Cancel. */
        /* The page's reset zeroes every margin, which also strips the
           browser's own centring of a dialog, so it is placed here: centred
           across, and in the top third rather than the middle, so the phone
           keyboard opening under it never covers the field. */
        .login-dialog {
            position: fixed;
            inset: 0;
            margin: max(14vh, 24px) auto auto;
            height: fit-content;
            max-height: calc(100vh - 48px);
            border: 1px solid var(--line);
            padding: 22px 20px 20px;
            width: min(calc(100vw - 32px), 380px);
            color: var(--ink);
            background: var(--surface);
            box-shadow: 0 18px 48px rgba(17, 18, 20, 0.18);
        }

        .login-dialog::backdrop {
            background: rgba(17, 18, 20, 0.45);
        }

        .login-dialog h2 {
            font-family: var(--display);
            font-weight: 600;
            font-size: 1.05rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin: 0 0 6px;
        }

        .login-dialog p {
            font-size: 0.9rem;
            line-height: 1.45;
            color: var(--ink-2);
            margin: 0 0 14px;
        }

        .login-dialog label {
            display: block;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .login-input {
            display: block;
            width: 100%;
            font: inherit;
            font-size: 16px; /* 16px stops iOS zooming into the field */
            border: 1px solid var(--line);
            padding: 9px 10px;
            background: #ffffff;
            color: var(--ink);
        }

        .login-input:focus-visible,
        .login-btn:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 2px;
        }

        .login-msg {
            min-height: 1.3em;
            margin: 8px 0 0 !important;
            font-size: 0.82rem !important;
        }

        .login-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 10px;
        }

        .login-btn {
            appearance: none;
            border: 0;
            cursor: pointer;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.8rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 9px 16px;
            background: var(--ink);
            color: #ffffff;
        }

        .login-btn.secondary {
            background: transparent;
            color: var(--ink-2);
            box-shadow: inset 0 0 0 1px var(--line);
        }

        /* A team the GTHL has no logo for, usually an East team in an
           interlocking game, gets its initials in the same footprint. */
        .team-mono {
            display: inline-grid;
            place-items: center;
            border-radius: 50%; /* a round badge, like the crests it stands in for */
            background: #e9e7ec;
            color: #514c57;
            font-family: var(--body);
            font-weight: 700;
            font-size: 0.56rem;
            letter-spacing: 0.02em;
            line-height: 1;
        }

        .face-team .team-mono {
            font-size: 0.72rem;
        }

        /* Filtering is a class on the wrapper, set in the generated HTML so the
           list is right before any script runs. A week with none of our games
           goes with them, and each week shows the count for the active view. */
        .filter-ours .game:not(.is-ours),
        .filter-ours .week[data-ours="0"],
        .filter-ours .count-all,
        .sched-weeks:not(.filter-ours) .count-ours {
            display: none;
        }
"""

# Progressive enhancement: the generated HTML already carries the default
# filter class, so the list is correct before this runs and correct if it never
# does. The script switches between the two views and remembers the choice,
# points directions at Apple Maps on iPhone and iPad, and unlocks team events.
#
# enhance() runs on load and again after the team version of the schedule is
# swapped in, since that replaces the elements it works on.
SCHEDULE_JS = """
    <script>
    (function () {
      var FILTER_KEY = 'eagles-schedule-filter';
      var PASS_KEY = 'eagles-team-password';
      var TYPE_KEY = 'eagles-type-filter';
      var block = document.querySelector('[data-schedule-block]');
      var payloadEl = document.getElementById('team-events');
      var publicHtml = block ? block.innerHTML : '';

      function store(key, value) {
        try {
          if (value === null) localStorage.removeItem(key);
          else localStorage.setItem(key, value);
        } catch (e) {}
      }
      function stored(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
      }

      // Directions open in the phone's own maps app. Every link is Google Maps
      // in the HTML, which Android opens in Google Maps and a computer in the
      // browser; on iPhone and iPad it is swapped for Apple Maps. iPadOS
      // reports itself as a Mac, so a Mac with a touch screen counts as an iPad.
      var ua = navigator.userAgent;
      var apple = /iPhone|iPad|iPod/.test(ua) ||
                  (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);

      // LiveBarn links: nothing before puck drop, LIVE for the first hour,
      // Rewatch after. The page is rebuilt hourly, so the state is worked out
      // here, from each link's start time, and refreshed every minute.
      function updateStreams() {
        var now = Date.now();
        document.querySelectorAll('.game-watch[data-start]').forEach(function (a) {
          var minutes = (now - Date.parse(a.dataset.start)) / 60000;
          var state = minutes < 0 ? 'upcoming' : minutes < 60 ? 'live' : 'rewatch';
          var text = { upcoming: 'Watch', live: 'Live', rewatch: 'Rewatch' }[state];
          a.hidden = state === 'upcoming';
          a.classList.remove('is-upcoming', 'is-live', 'is-rewatch');
          a.classList.add('is-' + state);
          if (!a.classList.contains('icon-btn')) a.textContent = text;
          a.setAttribute('aria-label', text + ': ' + (a.dataset.label || 'LiveBarn'));
        });
        document.querySelectorAll('[data-live-start]').forEach(function (flag) {
          var minutes = (now - Date.parse(flag.dataset.liveStart)) / 60000;
          var live = minutes >= 0 && minutes < 60;
          flag.hidden = !live;
          var row = flag.closest('.game');
          if (row) row.classList.toggle('is-live', live);
        });
      }
      setInterval(updateStreams, 60000);

      function enhance() {
        updateStreams();
        if (apple) {
          document.querySelectorAll('a[data-apple-maps]').forEach(function (a) {
            a.href = a.dataset.appleMaps;
            a.removeAttribute('target');
          });
        }

        // A row with details opens on tap (or Enter / Space), except when
        // the tap is on a link inside it, such as the rink's directions.
        document.querySelectorAll('.game.has-details').forEach(function (row) {
          var toggle = function () {
            var open = row.classList.toggle('is-open');
            row.setAttribute('aria-expanded', String(open));
          };
          row.addEventListener('click', function (event) {
            if (event.target.closest('a, button')) return;
            toggle();
          });
          row.addEventListener('keydown', function (event) {
            if (event.target !== row) return;
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              toggle();
            }
          });
        });

        // Two filters: whose games (Eagles / All) and, logged in, what kind
        // (Games / Practices / All). The Eagles / All choice also works
        // without scripting, through the filter-ours class; the kind filter
        // only exists logged in, which needs scripting anyway. A week shows
        // only while something in it passes both.
        var view = document.querySelector('[data-schedule-view]');
        var whoButtons = document.querySelectorAll('[data-filter]');
        var typeButtons = document.querySelectorAll('[data-type-filter]');
        if (view && whoButtons.length) {
          var who = view.classList.contains('filter-ours') ? 'ours' : 'all';
          var kind = 'all';
          var render = function () {
            view.classList.toggle('filter-ours', who === 'ours');
            whoButtons.forEach(function (b) {
              b.setAttribute('aria-pressed', String(b.dataset.filter === who));
            });
            typeButtons.forEach(function (b) {
              b.setAttribute('aria-pressed', String(b.dataset.typeFilter === kind));
            });
            view.querySelectorAll('.week').forEach(function (week) {
              var any = false;
              week.querySelectorAll('.game').forEach(function (row) {
                var show = (who === 'all' || row.classList.contains('is-ours')) &&
                           (kind === 'all' || row.dataset.type === kind);
                row.hidden = !show;
                any = any || show;
              });
              week.hidden = !any;
            });
          };
          var savedWho = stored(FILTER_KEY);
          // Only honour a stored choice the page can actually show.
          if (savedWho === 'all' || (savedWho === 'ours' && view.dataset.hasOurs === '1')) {
            who = savedWho;
          }
          var savedKind = stored(TYPE_KEY);
          if (typeButtons.length && (savedKind === 'game' || savedKind === 'practice')) {
            kind = savedKind;
          }
          render();
          whoButtons.forEach(function (b) {
            b.addEventListener('click', function () {
              who = b.dataset.filter; store(FILTER_KEY, who); render();
            });
          });
          typeButtons.forEach(function (b) {
            b.addEventListener('click', function () {
              kind = b.dataset.typeFilter; store(TYPE_KEY, kind); render();
            });
          });
        }
      }

      // The log-in box. Log in decrypts the team version and swaps it in;
      // Log out forgets the password and puts the public version back.
      var dialog = document.getElementById('login-dialog');
      var authLink = document.querySelector('[data-auth-link]');

      function setAuthLink(loggedIn) {
        if (!authLink) return;
        authLink.textContent = loggedIn ? 'Log out' : 'Team Login';
        if (loggedIn) authLink.dataset.loggedIn = '1';
        else delete authLink.dataset.loggedIn;
      }

      function openLogin(message) {
        if (!dialog) return;
        var msg = dialog.querySelector('.login-msg');
        msg.textContent = message || '';
        if (dialog.showModal) dialog.showModal(); else dialog.setAttribute('open', '');
        dialog.querySelector('input').focus();
      }

      function logOut() {
        store(PASS_KEY, null);
        block.innerHTML = publicHtml;
        setAuthLink(false);
        enhance();
      }

      if (authLink && dialog) {
        authLink.addEventListener('click', function (event) {
          event.preventDefault();
          if (authLink.dataset.loggedIn) logOut(); else openLogin();
        });
        var form = dialog.querySelector('form');
        form.addEventListener('submit', function (event) {
          event.preventDefault();
          var input = form.querySelector('input');
          var msg = dialog.querySelector('.login-msg');
          msg.textContent = 'Logging in\u2026';
          unlock(input.value).then(function (ok) {
            if (ok) {
              input.value = '';
              msg.textContent = '';
              dialog.close ? dialog.close() : dialog.removeAttribute('open');
            } else {
              msg.textContent = 'That password didn\u2019t work. Check the team message for it.';
              input.select();
            }
          });
        });
        dialog.querySelector('[data-login-cancel]').addEventListener('click', function () {
          dialog.close ? dialog.close() : dialog.removeAttribute('open');
        });
      }

      function bytes(b64) {
        return Uint8Array.from(atob(b64), function (c) { return c.charCodeAt(0); });
      }

      // The team events are encrypted with the team password: PBKDF2-SHA256
      // for the key, AES-GCM for the data (team_crypto.py writes them). A wrong
      // password fails the AES-GCM check rather than producing garbage.
      function unlock(password) {
        if (!payloadEl || !password || !window.crypto || !crypto.subtle) {
          return Promise.resolve(false);
        }
        var p = JSON.parse(payloadEl.textContent);
        return crypto.subtle.importKey('raw', new TextEncoder().encode(password),
                                       'PBKDF2', false, ['deriveKey'])
          .then(function (base) {
            return crypto.subtle.deriveKey(
              { name: 'PBKDF2', salt: bytes(p.salt), iterations: p.iter, hash: 'SHA-256' },
              base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
          })
          .then(function (key) {
            return crypto.subtle.decrypt({ name: 'AES-GCM', iv: bytes(p.iv) }, key, bytes(p.ct));
          })
          .then(function (plain) {
            block.innerHTML = new TextDecoder().decode(plain);
            store(PASS_KEY, password);
            setAuthLink(true);
            enhance();
            return true;
          })
          .catch(function () { return false; });
      }

      enhance();

      // A phone that logged in before logs in again on its own. If the
      // password has since changed, it is forgotten and the log-in box says
      // why. Arriving from another page's Log in link opens the box.
      var remembered = stored(PASS_KEY);
      if (remembered && payloadEl) {
        unlock(remembered).then(function (ok) {
          if (ok) return;
          store(PASS_KEY, null);
          setAuthLink(false);
          openLogin('The team password has changed. Enter the new one.');
        });
      } else if (location.hash === '#login' && payloadEl) {
        history.replaceState(null, '', location.pathname);
        openLogin();
      }
    })();
    </script>
"""

# Without scripting the toggle cannot work, so hide it and show every game
# rather than stranding the reader on a filtered list they cannot leave.
SCHEDULE_NOSCRIPT = """    <noscript>
        <style>
            /* Without scripting the toggle cannot work, so hide it and show
               every game rather than stranding the reader on a filtered list
               they cannot leave. Same specificity as the rules that hide, and
               later, so these win without !important. */
            .sched-filter { display: none; }

            .filter-ours .game:not(.is-ours),
            .filter-ours .week[data-ours="0"] {
                display: grid;
            }

            .filter-ours .count-all { display: inline; }
            .filter-ours .count-ours { display: none; }

            /* Logging in needs scripting to decrypt the team events. */
            .mastnav-auth { display: none; }
        </style>
    </noscript>
"""

_CHROME_CSS = """
        .notice,
        .error {
            position: relative;
            overflow: hidden;
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

        /* A footnote to the table above it, on the same white. No underline
           or help cursor on the time: there is no hover on a phone, so the
           title is a bonus for anyone who looks rather than an advertised
           affordance. */
        .content-meta {
            font-size: 0.68rem;
            letter-spacing: 0.02em;
            color: #a4a4a4;
            text-align: right;
            margin-top: 10px;
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

            td .team-logo {
                display: none;
            }
        }
"""

# --- Sponsors ---------------------------------------------------------------
# The club's sponsors run as a slim strip under the tabs on every page, scrolling
# slowly sideways in a loop. It reads as part of the page rather than as an ad:
# no box around a mark, no dimming, each logo shown unaltered on white.
#
# The loop is the sponsor set repeated until one half of the track is wider
# than any screen, then the whole track slides left by exactly half, so the
# seam never shows. Only the first set is announced to screen readers and
# reachable by keyboard; the copies are decoration. With reduced motion asked
# for, the strip stands still and can be swiped instead.

SPONSORS = [
    {
        "name": "Recruit Connect",
        "url": "https://www.recruit-connect.ca/",
        "logo": "assets/recruit-connect.png",
        "width": 540,
        "height": 247,
        # Optical scale, not bounding-box scale. A stacked logo needs more
        # height than a single-line wordmark to carry the same weight, so each
        # mark is sized against the strip height by its own factor.
        "scale": 1.0,
    },
    {
        "name": "Tasios Orthodontics",
        "url": "https://tasiosortho.com/",
        "logo": "assets/tasios-orthodontics.png",
        "width": 502,
        "height": 154,
        "scale": 0.74,
    },
    {
        "name": "Performance Auto Group",
        "url": "https://www.performance.ca/",
        "logo": "assets/performance-auto-group.png",
        "width": 650,
        "height": 203,
        "scale": 0.74,
    },
    {
        "name": "Shoxs Billiard Lounge",
        "url": "https://shoxs.ca/",
        "logo": "assets/shoxs.jpg",
        "width": 640,
        "height": 256,
        # The oval fills its whole frame, so it needs more height than the
        # wordmarks to read at the same size.
        "scale": 1.1,
    },
]

# How many times the sponsor set repeats in each half of the track. One set of
# four logos with their gaps measures about 490px, so four sets (about 1960px)
# clear a 1920px screen. Adding a sponsor widens the set and speeds the strip
# up: re-check this and the animation time so it stays near 33px a second.
_SPONSOR_SETS_PER_HALF = 4

_SPONSOR_CSS = """
        .sponsor-strip {
            --sponsor-height: 34px;
            --sponsor-gap: clamp(40px, 7vw, 72px);
            background: #ffffff;
            border-bottom: 1px solid var(--line);
            overflow: hidden;
            padding: 8px 0;
        }

        .sponsor-track {
            display: flex;
            width: max-content;
            animation: sponsor-scroll 60s linear infinite;
        }

        .sponsor-strip:hover .sponsor-track,
        .sponsor-strip:focus-within .sponsor-track {
            animation-play-state: paused;
        }

        .sponsor-set {
            display: flex;
            align-items: center;
            gap: var(--sponsor-gap);
            padding-right: var(--sponsor-gap);
        }

        .sponsor-link {
            display: block;
            line-height: 0;
            flex-shrink: 0;
        }

        .sponsor-link:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 4px;
        }

        .sponsor-logo {
            height: calc(var(--sponsor-height) * var(--scale, 1));
            width: auto;
            display: block;
        }

        @keyframes sponsor-scroll {
            to {
                transform: translateX(-50%);
            }
        }

        /* Standing still: one set, centred, and swipeable if it ever outgrows
           the screen. */
        @media (prefers-reduced-motion: reduce) {
            .sponsor-strip {
                overflow-x: auto;
                scrollbar-width: none;
            }

            .sponsor-strip::-webkit-scrollbar {
                display: none;
            }

            .sponsor-track {
                animation: none;
                margin: 0 auto;
            }

            .sponsor-set[aria-hidden="true"] {
                display: none;
            }
        }
"""


def _sponsor_set(decorative):
    """One run of every sponsor's logo. Copies are hidden from assistive tech."""
    hidden = ' aria-hidden="true"' if decorative else ''
    html = f'                <div class="sponsor-set"{hidden}>\n'
    for sponsor in SPONSORS:
        tab = ' tabindex="-1"' if decorative else ''
        alt = '' if decorative else sponsor['name']
        html += (f'                    <a class="sponsor-link" href="{sponsor["url"]}"{tab}\n'
                 f'                       target="_blank" rel="noopener noreferrer">'
                 f'<img class="sponsor-logo" src="{sponsor["logo"]}" alt="{alt}"\n'
                 f'                         style="--scale: {sponsor["scale"]}" '
                 f'width="{sponsor["width"]}" height="{sponsor["height"]}"></a>\n')
    return html + '                </div>\n'


def sponsor_strip():
    """The scrolling sponsor strip that sits under the tabs on every page."""
    sets = _SPONSOR_SETS_PER_HALF * 2
    html = ('        <aside class="sponsor-strip" aria-label="Our sponsors">\n'
            '            <div class="sponsor-track">\n')
    for n in range(sets):
        html += _sponsor_set(decorative=n > 0)
    return html + '            </div>\n        </aside>\n'


def freshness(timestamp, refresh_note="Refreshes hourly"):
    """
    How fresh the page is, as one quiet line under the table it describes.

    It sits inside the content, on the same white as the table, rather than in
    a band of its own: it is a footnote to the data above it, not a section of
    the page. The wall-clock time and the refresh cadence are in the title.
    """
    detail = " · ".join(x for x in (absolute_time(timestamp), refresh_note) if x)
    return (f'            <p class="content-meta">Updated '
            f'<time datetime="{machine_time(timestamp)}" title="{detail}">'
            f'{relative_time(timestamp)}</time></p>\n')


def page_end():
    """
    What closes every page. Nothing now: the sponsors moved up under the tabs.
    Kept so the generators keep one place to add a footer.
    """
    return ""


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
            border-top: none;
        }

        .info-box {
            background: #fafafa;
            border: 1px solid var(--line);
            border-left: 3px solid var(--crest);
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

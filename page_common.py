#!/usr/bin/env python3
"""
Pieces shared by the three page generators: the "last updated" line, the
filter badges in the header, and the styling for a neutral notice box.
"""

import html
import json
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

# The red play button that marks a link to a game's film on YouTube, wherever the site shows one.
FILM_ICON = ('<svg class="film-icon" viewBox="0 0 20 14" width="20" height="14" aria-hidden="true">'
             '<rect width="20" height="14" rx="4" fill="#ff0000"/><path d="M8 4l5 3-5 3z" fill="#ffffff"/></svg>')

# On a game page the film button is sealed with the team password, like the schedule's team version, and put in place once the
# phone's saved password opens it. Without the password the page carries nothing but the sealed text.
REVIEW_JS = r"""
      // The review: the game's goals and penalties beside the film, in a full-screen layer. It is built only when a signed-in viewer
      // opens it, and the video player's script is loaded then and not before.
      function review(film) {
        var id = null;
        try { var u = new URL(film.url); id = u.searchParams.get('v') || u.pathname.split('/').pop(); } catch (e) {}
        if (!id || !/^[\w-]{6,}$/.test(id) || typeof film.api !== 'string' || film.api.indexOf('https://') !== 0) return;
        var at = {}, state = null;
        film.moments.forEach(function (m) {
          var k = m.kind + '|' + m.period + '|' + m.clock;
          if (typeof m.t === 'number' && m.t >= 0 && !(k in at)) at[k] = Math.floor(m.t);
        });
        function left(clock) { var x = clock.split(':'); return (+x[0]) * 60 + (+x[1]); }
        // Goals and penalties that have a placed time and a row on the game sheet, in game order.
        function events() {
          var out = [];
          Array.prototype.forEach.call(document.querySelectorAll('li[data-m]'), function (li) {
            var k = li.getAttribute('data-m'), x = k.split('|');
            if (!(k in at) || (x[0] !== 'goal' && x[0] !== 'penalty')) return;
            var what = li.querySelector('.sheet-what');
            if (!what) return;
            out.push({ key: k, t: at[k], p: +x[1], c: left(x[2]), li: li, what: what });
          });
          out.sort(function (a, b) { return a.p - b.p || b.c - a.c; });
          return out;
        }
        function el(tag, cls, text) {
          var n = document.createElement(tag);
          if (cls) n.className = cls;
          if (text) n.textContent = text;
          return n;
        }
        function watchUrl(t) { return film.url + (t > 0 ? (film.url.indexOf('?') < 0 ? '?' : '&') + 't=' + Math.floor(t) : ''); }
        function show(t, trigger) {
          if (state) return;
          var list = events(), rows = [], timer = null, player = null, ready = false, pending = null, now = -1;
          var root = el('div', 'rv'), box = el('div', 'rv-box' + (list.length ? '' : ' rv-solo'));
          root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true'); root.setAttribute('aria-label', 'Game film');
          var head = el('div', 'rv-head'), close = el('button', 'rv-close');
          close.type = 'button'; close.setAttribute('aria-label', 'Close'); close.setAttribute('data-tip', 'Close');
          close.innerHTML = '<svg viewBox="0 0 14 14" width="14" height="14" aria-hidden="true"><path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/></svg>';
          head.appendChild(el('span', 'rv-title', 'Game film')); head.appendChild(close);
          var stage = el('div', 'rv-stage'), frame = el('div', 'rv-frame'), mount = el('div'), ext = el('a', 'rv-open');
          frame.appendChild(mount); stage.appendChild(frame);
          ext.target = '_blank'; ext.rel = 'noopener noreferrer'; ext.href = watchUrl(t);
          ext.setAttribute('data-tip', 'Open on YouTube');
          ext.insertAdjacentHTML('beforeend', ICON); ext.appendChild(el('span', '', 'Open on YouTube'));
          stage.appendChild(ext);
          var ul = el('ul', 'rv-list');
          list.forEach(function (ev) {
            var li = el('li'), btn = el('button', 'rv-row'), when = ev.li.querySelector('.sheet-when'), w = el('span', 'sheet-what');
            btn.type = 'button';
            var team = ev.what.getAttribute('data-tip') || '';
            var logo = ev.what.querySelector('.team-logo');
            if (logo) w.appendChild(logo.cloneNode(true));
            Array.prototype.forEach.call(ev.what.children, function (c) {
              if (c.tagName === 'SPAN') w.appendChild(c.cloneNode(true));
            });
            btn.appendChild(el('span', 'sheet-when', when ? when.textContent : ''));
            btn.appendChild(w);
            btn.setAttribute('aria-label', (when ? when.textContent + ', ' : '') + team + ', ' + w.textContent.replace(/\s+/g, ' ').trim());
            btn.addEventListener('click', function () { go(ev.t); });
            li.appendChild(btn); ul.appendChild(li); rows.push({ ev: ev, btn: btn });
          });
          if (list.length) box.appendChild(ul);
          box.appendChild(stage);
          root.appendChild(head); root.appendChild(box);
          var page = document.querySelector('.container'), html = document.documentElement, was = [html.style.overflow, document.body.style.overflow];
          if (page) page.setAttribute('inert', '');
          html.style.overflow = 'hidden'; document.body.style.overflow = 'hidden';
          document.body.appendChild(root);

          function mark(ct) {
            var best = -1;
            rows.forEach(function (r, i) { if (r.ev.t <= ct) best = i; });
            if (best === now) return;
            now = best;
            rows.forEach(function (r, i) {
              r.btn.classList.toggle('is-now', i === best);
              if (i === best) r.btn.setAttribute('aria-current', 'true'); else r.btn.removeAttribute('aria-current');
            });
            if (best >= 0) {
              var b = rows[best].btn, top = b.offsetTop - ul.offsetTop;
              if (top < ul.scrollTop || top + b.offsetHeight > ul.scrollTop + ul.clientHeight) ul.scrollTop = Math.max(0, top - 8);
            }
          }
          function tick() { try { mark(player.getCurrentTime()); } catch (e) {} }
          function go(s) {
            ext.href = watchUrl(s);
            mark(s);
            if (player && ready) { player.seekTo(s, true); player.playVideo(); } else { pending = s; }
          }
          function build() {
            if (!state) return;
            player = new YT.Player(mount, {
              videoId: id, width: '100%', height: '100%',
              playerVars: Object.assign({ rel: 0, modestbranding: 1, playsinline: 1, autoplay: 1 }, t > 0 ? { start: Math.floor(t) } : {}),
              events: {
                onReady: function () {
                  ready = true;
                  if (pending !== null) { player.seekTo(pending, true); player.playVideo(); pending = null; }
                },
                onStateChange: function (e) {
                  clearInterval(timer); timer = null;
                  if (e.data === 1) { timer = setInterval(tick, 500); }
                  tick();
                }
              }
            });
          }
          function shut() {
            if (!state) return;
            state = null;
            clearInterval(timer);
            try { player && player.destroy(); } catch (e) {}
            document.removeEventListener('keydown', keys, true);
            document.removeEventListener('focusin', keep, true);
            root.remove();
            if (page) page.removeAttribute('inert');
            html.style.overflow = was[0]; document.body.style.overflow = was[1];
            if (trigger && document.contains(trigger)) trigger.focus();
          }
          function keys(e) {
            if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); shut(); return; }
            if (e.key !== 'Tab') return;
            var f = Array.prototype.filter.call(root.querySelectorAll('button, a[href], iframe'), function (n) { return n.offsetParent !== null; });
            if (!f.length) return;
            var first = f[0], last = f[f.length - 1];
            if (!root.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
            else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
            else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
          }
          function keep(e) { if (state && !root.contains(e.target)) close.focus(); }
          state = { shut: shut };
          close.addEventListener('click', shut);
          document.addEventListener('keydown', keys, true);
          document.addEventListener('focusin', keep, true);
          mark(t);
          close.focus();
          if (window.YT && YT.Player) build();
          else {
            var prior = window.onYouTubeIframeAPIReady;
            window.onYouTubeIframeAPIReady = function () { if (prior) prior(); build(); };
            if (!document.getElementById('rv-api')) {
              var s = document.createElement('script');
              s.id = 'rv-api'; s.src = film.api; s.async = true;
              document.head.appendChild(s);
            }
          }
        }
        // A plain click on a mark, a row or the film button opens the review; a modified click or a middle click still goes to the video.
        document.addEventListener('click', function (e) {
          if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          var a = e.target.closest && e.target.closest('a.is-film, .match-actions a.film');
          if (!a || a.closest('.rv')) return;
          e.preventDefault();
          var t = parseFloat(a.getAttribute('data-t'));
          show(isNaN(t) ? 0 : t, a);
        });
      }
"""

FILM_JS = """
    <script>
    (function () {
      var el = document.getElementById('game-film'), pw = null;
      try { pw = localStorage.getItem('eagles-team-password'); } catch (e) {}
      if (!el || !pw || !window.crypto || !crypto.subtle) return;
      var p = JSON.parse(el.textContent);
      var ICON = __FILM_ICON__;
      // A mark or row on the game sheet whose moment is placed on the film becomes a link to the video at that second.
      function link(film) {
        var at = {};
        film.moments.forEach(function (m) {
          var k = m.kind + '|' + m.period + '|' + m.clock;
          if (typeof m.t === 'number' && m.t >= 0 && !(k in at)) at[k] = Math.floor(m.t);
        });
        Array.prototype.forEach.call(document.querySelectorAll('[data-m]'), function (node) {
          var k = node.getAttribute('data-m');
          if (!(k in at)) return;
          var href = film.url + (at[k] > 0 ? (film.url.indexOf('?') < 0 ? '?' : '&') + 't=' + at[k] : '');
          var row = node.tagName === 'LI', el = row ? node.querySelector('.sheet-what') : node;
          if (!el) return;
          var a = document.createElement('a');
          Array.prototype.forEach.call(el.attributes, function (x) { a.setAttribute(x.name, x.value); });
          while (el.firstChild) a.appendChild(el.firstChild);
          a.removeAttribute('role');
          a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer';
          a.classList.add('is-film');
          var tip = a.getAttribute('data-tip'), label = a.getAttribute('aria-label');
          a.setAttribute('data-tip', (tip ? tip + '||' : '') + 'Watch on YouTube');
          a.setAttribute('data-t', at[k]);
          a.setAttribute('aria-label', (label ? label + ', ' : '') + 'watch on YouTube');
          if (row) a.insertAdjacentHTML('beforeend', ICON);
          el.parentNode.replaceChild(a, el);
        });
      }
__REVIEW__
      function b(s) { return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }); }
      crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey'])
        .then(function (base) {
          return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: b(p.salt), iterations: p.iter, hash: 'SHA-256' },
                                         base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
        })
        .then(function (key) { return crypto.subtle.decrypt({ name: 'AES-GCM', iv: b(p.iv) }, key, b(p.ct)); })
        .then(function (plain) {
          var text = new TextDecoder().decode(plain), film = null;
          try { film = JSON.parse(text); } catch (e) {}
          var slot = document.querySelector('.match-actions');
          if (slot) slot.insertAdjacentHTML('afterbegin', film && typeof film.html === 'string' ? film.html : text);
          if (film && typeof film.url === 'string' && film.url.indexOf('https://') === 0 && Array.isArray(film.moments)) {
            link(film);
            review(film);
          }
        })
        .catch(function () {});
    })();
    </script>
"""
FILM_JS = FILM_JS.replace("__REVIEW__", REVIEW_JS.rstrip("\n")).replace("__FILM_ICON__", json.dumps(FILM_ICON))



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
    html = f"""        <div class="topbar">
        <header class="masthead">
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
    html += "        </nav>\n        </div>\n"
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


def rank_standings(standings):
    """
    The standings in the GTHL's order: points, then the tie-breaking rules of
    Regulation 12.2 (standings_rules.py). Position counts 1, 2, 3...; Rank
    is the place shown, shared by teams the rules cannot separate, which have
    Tied set.
    """
    import standings_rules
    return standings_rules.rank(standings)


# Fields rank_standings adds that are not standings columns.
RANK_FIELDS = {"Rank", "Tied"}


def ordinal(n):
    """1 -> '1st', 13 -> '13th'."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def rank_label(row):
    """The rank column: '5', or 'T5' for a place shared with another team."""
    rank = row.get("Rank", row.get("Position", ""))
    return f"T{rank}" if row.get("Tied") else str(rank)


def place_label(row):
    """In words: '5th', or 'T-5th' for a shared place."""
    rank = row.get("Rank", row.get("Position", 0))
    return f"T-{ordinal(rank)}" if row.get("Tied") else ordinal(rank)


def logo_src(team):
    """The path of a team's cached logo, or None when there is none."""
    filename = f"{slug(team)}.png"
    return f"assets/logos/{filename}" if os.path.exists(os.path.join(LOGO_DIR, filename)) else None


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

        /* No double-tap zoom: a quick second tap (say, a near miss on an
           arrow) must not zoom the page. Pinch zoom still works. */
        html {
            -webkit-text-size-adjust: 100%;
            touch-action: manipulation;
        }

        a,
        button,
        [role="button"] {
            touch-action: manipulation;
        }

        body {
            font-family: var(--body);
            background: var(--surface);
            color: var(--ink);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }

        /* The page fills the screen even when there is little on it: the
           grey content area stretches down to the bottom. */
        .container {
            background: var(--surface);
            min-height: 100vh;
            min-height: 100dvh;
            display: flex;
            flex-direction: column;
        }

        /* A faint grey behind the content only, so the white tables and game
           cards read as objects on it. The masthead and sponsors stay white. */
        .content {
            flex: 1 0 auto;
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

_LINK_CSS = """
        /* A team's name, wherever it is listed, leads to its page. */
        .team-link {
            color: inherit;
            text-decoration: none;
        }

        .team-link:hover .team-cell > span,
        .team-link:focus-visible .team-cell > span,
        a.team-link:hover:not(:has(.team-cell)),
        a.team-link:focus-visible:not(:has(.team-cell)) {
            text-decoration: underline;
            text-underline-offset: 3px;
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

        .table-wrapper th.rank {
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

        /* The controls, left-aligned and wrapping: Eagles / West, (logged
           in) Games / All, and Day / Week / Month / Season. The controls say
           what the list is, so the "Schedule" heading is there for screen
           readers only. */
        .sched-head {
            display: flex;
            justify-content: flex-start;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .sched-head h2 {
            position: absolute;
            width: 1px;
            height: 1px;
            overflow: hidden;
            clip: rect(0 0 0 0);
            white-space: nowrap;
        }

        /* Segmented controls: a soft grey track, the chosen option on a
           raised white chip. Quiet enough to sit above the schedule without
           competing with it. */
        .sched-filter {
            display: inline-flex;
            gap: 2px;
            padding: 3px;
            background: #ebebee;
            border-radius: 999px;
        }

        .sched-filter-btn {
            appearance: none;
            border: 0;
            border-radius: 999px;
            background: transparent;
            cursor: pointer;
            font-family: var(--body);
            font-weight: 600;
            font-size: 0.82rem;
            color: var(--ink-2);
            padding: 6px 13px;
            display: inline-flex;
            align-items: baseline;
            gap: 5px;
            white-space: nowrap;
            transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
        }

        /* The team picker: a select dressed as a segment, with a caret. */
        .team-pick {
            position: relative;
            padding-right: 26px !important;
        }



        /* The native select lies invisibly over the label, so a tap opens
           the phone's own picker while the label shows the choice. */
        .team-pick select {
            position: absolute;
            inset: 0;
            width: 100%;
            opacity: 0;
            font-size: 16px;   /* iOS zooms into smaller form fields */
            cursor: pointer;
        }

        .pick-text {
            max-width: 9.5rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .team-pick select:focus {
            outline: none;
        }

        .team-pick:focus-within {
            outline: 2px solid var(--brand);
            outline-offset: 1px;
        }

        .team-pick::after {
            content: "";
            position: absolute;
            right: 11px;
            top: 50%;
            width: 6px;
            height: 6px;
            border-right: 1.6px solid currentColor;
            border-bottom: 1.6px solid currentColor;
            transform: translateY(-70%) rotate(45deg);
            pointer-events: none;
        }

        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            overflow: hidden;
            clip: rect(0 0 0 0);
            white-space: nowrap;
        }

        .sched-filter-btn:hover {
            color: var(--ink);
        }

        .sched-filter-btn[aria-pressed="true"] {
            background: var(--surface);
            color: var(--ink);
            box-shadow: 0 1px 2px rgba(20, 22, 26, 0.14), 0 0 0 0.5px rgba(20, 22, 26, 0.06);
        }

        .sched-filter-btn:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 1px;
        }

        /* --- Day / Week / Month / Season, and the arrows --- */
        /* The period's heading doubles as its navigation: the name in the
           display face (red while it contains today), the dates or year in
           grey beside it, the counts underneath, and Today and the round
           arrows at the right. */
        .period-head {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            column-gap: 10px;
            padding: 6px 2px 10px;
        }

        .period-title {
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            column-gap: 8px;
            min-width: 0;
        }

        .period-name {
            font-family: var(--display);
            font-weight: 600;
            font-size: 1.3rem;
            line-height: 1.15;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: var(--ink);
        }

        .period-name.now {
            color: var(--brand);
        }

        .period-sub {
            font-size: 0.84rem;
            font-weight: 500;
            color: var(--ink-3);
            white-space: nowrap;
        }

        .period-count {
            grid-column: 1;
            font-size: 0.8rem;
            color: var(--ink-3);
            margin-top: 2px;
        }

        .period-step[hidden] {
            display: none;
        }

        .period-nav {
            grid-column: 2;
            grid-row: 1 / span 2;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Round arrow buttons. */
        .period-step {
            appearance: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            padding: 0;
            border: 0;
            border-radius: 50%;
            background: #ebebee;
            color: var(--ink);
            cursor: pointer;
            transition: background 0.15s ease;
        }

        .period-step svg {
            width: 14px;
            height: 14px;
            fill: none;
            stroke: currentColor;
            stroke-width: 2.2;
            stroke-linecap: round;
            stroke-linejoin: round;
        }

        /* A bigger target than the circle, so a near miss still counts. */
        .period-step {
            position: relative;
        }

        .period-step::after {
            content: "";
            position: absolute;
            inset: -7px -4px;
        }

        .period-step:hover {
            background: #e0e0e4;
        }

        .period-step:disabled {
            background: #f1f1f3;
            color: #c4c4ca;
            cursor: default;
        }

        .period-today {
            appearance: none;
            border: 0;
            background: none;
            color: var(--brand);
            font-family: var(--body);
            font-weight: 600;
            font-size: 0.82rem;
            padding: 6px 8px;
            cursor: pointer;
        }

        .period-today[hidden] {
            display: none;
        }

        .period-step:focus-visible,
        .period-today:focus-visible {
            outline: 2px solid var(--brand);
            outline-offset: 2px;
        }

        @media (max-width: 519px) {
            /* Tight enough that Eagles / West and the period picker share
               the first line on a phone. */
            .sched-head .sched-filter-btn {
                padding: 6px 9px;
            }

            .period-today {
                padding: 6px 4px;
            }

            .period-step {
                width: 30px;
                height: 30px;
            }
        }

        .sched-empty {
            padding: 28px 12px;
            text-align: center;
            color: var(--ink-3);
            background: var(--surface);
            border: 1px solid var(--line);
        }

        .sched-empty[hidden] {
            display: none;
        }

        /* The filters hide rows and weeks with the hidden attribute; rows
           and weeks set their own display, so it has to be made to win. */
        .sched-weeks [hidden] {
            display: none !important;
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

        /* With scripting, the period's heading replaces the weeks' own, and
           the weeks run together as a single list. */
        /* Today's rows, in a week, month or season: the day reads TODAY in
           red and the row has a faint red tint. */
        .game.is-today {
            background: #fdf5f6;
        }

        .game.is-today .game-day {
            color: var(--brand);
        }

        /* Season view: a band naming the month where each one starts. */
        .game.month-start::before {
            content: attr(data-month);
            grid-column: 1 / -1;
            margin: -8px -12px -4px;
            padding: 6px 12px;
            background: var(--wash);
            border-bottom: 1px solid var(--line);
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.74rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--ink-2);
        }

        .by-period .week > .week-head {
            display: none;
        }

        .by-period .week:not([hidden]) ~ .week .week-games {
            border-top: 0;
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
            /* One fixed line, whether it holds a time or "Final". */
            line-height: 1.15rem;
            height: 1.15rem;
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

        /* On wide screens the venue and start time sit between the teams and
           the icons, inside the row's two lines. */
        .game-where {
            display: none;
        }

        @media (min-width: 900px) {
            .game-teams {
                grid-template-columns: minmax(0, 1fr) 13rem 10.5rem 1.8rem;
            }

            .game-teams > .game-where {
                grid-column: 2;
                grid-row: 1 / span 2;
                display: flex;
                flex-direction: column;
                justify-content: center;
                min-width: 0;
                padding-right: 10px;
                font-size: 0.8rem;
                line-height: 1.15rem;
                color: var(--ink-2);
            }

            .where-place {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .where-time {
                font-family: var(--display);
                font-variant-numeric: tabular-nums;
                color: var(--ink-3);
            }

            .game-teams > .game-icons {
                grid-column: 3;
                justify-content: flex-end;
            }

            .game-teams > .game-goals {
                grid-column: 4;
            }
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

        .icon-btn.game-video .film-icon {
            width: 17px;
            height: 12px;
            display: block;
            opacity: 0.9;
        }

        .icon-btn.game-video:hover .film-icon {
            opacity: 1;
        }

        .game-icons {
            gap: 2px;
        }

        .icon-btn.game-watch::before {
            content: none !important;
        }

        /* LiveBarn's mark. A live game says so with the LIVE flag in the
           time's place. */
        .icon-btn.game-watch img {
            width: 15px;
            height: 17px;
            display: block;
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

        /* Our own name is not bolded: the red bar marks our games, and bold is
           kept for the winner of a played game. */

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

        /* The same line height as a team's name, so a played game's row is
           no taller than an upcoming one. */
        .game-goals {
            align-self: center;
            line-height: 1.15;
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

        /* A team event's second line: where, as a game row's second team. */
        .event-where {
            font-size: 0.86rem;
            line-height: 1.25;
            color: var(--ink-3);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* "Exhibition", "Tournament": a quiet tag left of LiveBarn, a letter on
           a phone and the word on a wider screen. */
        .event-tag.soft {
            background: #ebebee;
            color: var(--ink-2);
        }

        .game-kind {
            margin-right: 2px;
        }

        .game-kind .kind-long {
            display: none;
        }

        @media (min-width: 620px) {
            .game-kind .kind-short {
                display: none;
            }

            .game-kind .kind-long {
                display: inline;
            }
        }

        /* LiveBarn's place in a row with a tag: always held, so the logo lines
           up with the rows above and below even before there is a link. */
        .watch-slot {
            display: inline-flex;
            width: 32px;
            justify-content: center;
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

        /* A league game's row leads to its page; what details it has show. */
        .game.is-link,
        .next.is-link {
            cursor: pointer;
        }

        .game.is-link:hover {
            background: #fafafb;
        }

        .game.is-link .game-details {
            display: flex;
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
      var PERIOD_KEY = 'eagles-schedule-period';
      var period = null;   // 'day', 'week', 'month' or 'season'
      var anchor = null;   // a day inside the period shown, 'YYYY-MM-DD'

      // Tooltips: anything with data-tip. One tooltip for the page, shown after a short pause on hover, at once on keyboard
      // focus and on tap. Lines are split on '||', and the first is a heading when there are several. Listening on the
      // document means the team version of the schedule, swapped in after log-in, gets them without further work.
      var tipEl = null, tipFor = null, tipTimer = null, tipAt = 0;
      function tipHide() {
        clearTimeout(tipTimer);
        if (tipEl) tipEl.style.display = 'none';
        tipFor = null;
      }
      function tipShow(el) {
        if (!tipEl) {
          tipEl = document.createElement('div');
          tipEl.className = 'tip';
          tipEl.setAttribute('role', 'tooltip');
          document.body.appendChild(tipEl);
        }
        var lines = el.getAttribute('data-tip').split('||'), logo = el.getAttribute('data-tip-logo');
        tipEl.textContent = '';
        lines.forEach(function (text, i) {
          var row = document.createElement('div');
          if (lines.length > 1 && i === 0) row.className = 'tip-head';
          if (logo && i === 0) {
            var img = document.createElement('img');
            img.className = 'tip-logo';
            img.alt = '';
            img.src = logo;
            row.appendChild(img);
          }
          row.appendChild(document.createTextNode(text));
          tipEl.appendChild(row);
        });
        tipEl.style.display = 'block';
        var r = el.getBoundingClientRect(), t = tipEl.getBoundingClientRect();
        var left = Math.max(8, Math.min(r.left + r.width / 2 - t.width / 2,
                                        document.documentElement.clientWidth - t.width - 8));
        var top = r.top - t.height - 10;
        if (top < 8) top = r.bottom + 10;
        tipEl.style.left = left + 'px';
        tipEl.style.top = top + 'px';
        tipFor = el;
        tipAt = Date.now();
      }
      function tipTarget(e) {
        return e.target && e.target.closest ? e.target.closest('[data-tip]') : null;
      }
      document.addEventListener('mouseover', function (e) {
        var t = tipTarget(e);
        if (!t || t === tipFor) return;
        clearTimeout(tipTimer);
        tipTimer = setTimeout(function () { tipShow(t); }, 120);
      });
      document.addEventListener('mouseout', function (e) {
        var t = tipTarget(e);
        if (t && !(e.relatedTarget && t.contains(e.relatedTarget))) tipHide();
      });
      document.addEventListener('focusin', function (e) {
        var t = tipTarget(e);
        if (t) tipShow(t);
      });
      document.addEventListener('focusout', tipHide);
      // A tap shows the tooltip and a second tap closes it; a touch also fires a hover, so a click straight after
      // the tooltip opened is ignored. A link just opens.
      document.addEventListener('click', function (e) {
        var t = tipTarget(e);
        if (!t) { tipHide(); return; }
        if (t.matches('a[href]')) return;
        if (tipFor === t && Date.now() - tipAt > 400) tipHide(); else tipShow(t);
      });
      window.addEventListener('scroll', tipHide, { passive: true });


      // Dates as 'YYYY-MM-DD' strings, which sort and compare as dates.
      function iso(d) {
        return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' +
               ('0' + d.getDate()).slice(-2);
      }
      function day(s) {
        var p = s.split('-');
        return new Date(+p[0], +p[1] - 1, +p[2]);
      }
      var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                    'August', 'September', 'October', 'November', 'December'];
      var DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      // A week's heading: This week, Next week, Last week, or "Week of Oct 26".
      function weekTitle(s, today) {
        var gap = Math.round((day(s) - day(range('week', today)[0])) / (7 * 86400000));
        if (gap === 0) return 'This week';
        if (gap === 1) return 'Next week';
        if (gap === -1) return 'Last week';
        return 'Week of ' + short(day(s));
      }
      // A day's heading: Today, Tomorrow, Yesterday, or "Thursday, Oct 15".
      function dayTitle(s, today) {
        var gap = Math.round((day(s) - day(today)) / 86400000);
        if (gap === 0) return 'Today';
        if (gap === 1) return 'Tomorrow';
        if (gap === -1) return 'Yesterday';
        return DAYS[day(s).getDay()] + ', ' + short(day(s));
      }
      function short(d) { return MONTHS[d.getMonth()].slice(0, 3) + ' ' + d.getDate(); }

      // [first day, day after the last] of the period around a day.
      function range(p, s) {
        var d = day(s);
        if (p === 'day') {
          return [s, iso(new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1))];
        }
        if (p === 'week') {
          var mon = new Date(d.getFullYear(), d.getMonth(), d.getDate() - (d.getDay() + 6) % 7);
          return [iso(mon), iso(new Date(mon.getFullYear(), mon.getMonth(), mon.getDate() + 7))];
        }
        if (p === 'month') {
          return [iso(new Date(d.getFullYear(), d.getMonth(), 1)),
                  iso(new Date(d.getFullYear(), d.getMonth() + 1, 1))];
        }
        return ['0000-00-00', '9999-99-99'];
      }
      function step(p, s, n) {
        var d = day(s);
        if (p === 'day') return iso(new Date(d.getFullYear(), d.getMonth(), d.getDate() + n));
        if (p === 'week') return iso(new Date(d.getFullYear(), d.getMonth(), d.getDate() + 7 * n));
        return iso(new Date(d.getFullYear(), d.getMonth() + n, 1));
      }
      function label(p, s, season) {
        var r = range(p, s);
        if (p === 'season') return season;
        var a = day(r[0]);
        if (p === 'day') return DAYS[a.getDay()].slice(0, 3) + ', ' + short(a);
        if (p === 'month') return MONTHS[a.getMonth()].slice(0, 3) + ' ' + a.getFullYear();
        var b = day(r[1]);
        b.setDate(b.getDate() - 1);
        return short(a) + '\u2013' + (a.getMonth() === b.getMonth() ? b.getDate() : short(b));
      }

      // A week heading's count of what is showing in it, e.g. "2 games · 1 practice".
      var KINDS = [['practice', 'practice', 'practices'], ['dryland', 'dryland', 'dryland'],
                   ['tournament', 'tournament', 'tournaments'], ['event', 'team event', 'team events']];
      function countText(rows) {
        var n = {};
        rows.forEach(function (r) { n[r.dataset.kind] = (n[r.dataset.kind] || 0) + 1; });
        var events = [];
        KINDS.forEach(function (k) {
          if (n[k[0]]) events.push(n[k[0]] + ' ' + (n[k[0]] === 1 ? k[1] : k[2]));
        });
        var games = n.game || 0;
        var parts = games || !events.length ? [games + (games === 1 ? ' game' : ' games')] : [];
        return parts.concat(events).join(' \u00b7 ');
      }
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
          var text = { upcoming: 'Watch', live: 'Live', rewatch: 'Watch' }[state];
          a.hidden = state === 'upcoming';
          a.classList.remove('is-upcoming', 'is-live', 'is-rewatch');
          a.classList.add('is-' + state);
          if (!a.classList.contains('icon-btn')) a.textContent = text;
          a.setAttribute('aria-label', text + ': ' + (a.dataset.label || 'LiveBarn'));
          if (a.hasAttribute('data-tip')) {
            a.setAttribute('data-tip', { upcoming: 'Watch live on LiveBarn', live: 'Live now on LiveBarn',
                                         rewatch: 'Watch on LiveBarn' }[state]);
          }
        });
        // LiveBarn: the rink's live camera until the first hour is up, then
        // the recording from puck drop. The big buttons say which.
        var BUTTON = { upcoming: 'Watch live on LiveBarn', live: 'Live now on LiveBarn',
                       rewatch: 'Watch on LiveBarn' };
        document.querySelectorAll('[data-replay][data-start]').forEach(function (a) {
          var minutes = (now - Date.parse(a.dataset.start)) / 60000;
          var state = minutes < 0 ? 'upcoming' : minutes < 60 ? 'live' : 'rewatch';
          a.href = state === 'rewatch' ? a.dataset.replay : a.dataset.live;
          if (a.classList.contains('match-btn')) {
            a.classList.remove('is-upcoming', 'is-live', 'is-rewatch');
            a.classList.add('is-' + state);
            var span = a.querySelector('span');
            if (span) span.textContent = BUTTON[state];
          }
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

      // "Today", "Tomorrow", "In 3 days", worked out from the reader's own
      // date, so a countdown is right however long ago the page was built.
      function updateCountdowns() {
        var now = new Date();
        var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        document.querySelectorAll('[data-countdown]').forEach(function (el) {
          var p = el.dataset.countdown.split('-');
          var days = Math.round((new Date(+p[0], +p[1] - 1, +p[2]) - today) / 86400000);
          if (days < 0) return;   // Past: the page's next rebuild replaces it.
          var text = days === 0 ? 'Today' : days === 1 ? 'Tomorrow' : 'In ' + days + ' days';
          el.textContent = el.hasAttribute('data-countdown-lower') ? text.toLowerCase() : text;
        });
      }
      updateCountdowns();
      setInterval(updateCountdowns, 60000);

      function enhance() {
        updateStreams();
        if (apple) {
          document.querySelectorAll('a[data-apple-maps]').forEach(function (a) {
            a.href = a.dataset.appleMaps;
            a.removeAttribute('target');
          });
        }

        // A locked team-event page's own Team Login button.
        document.querySelectorAll('[data-open-login]').forEach(function (b) {
          b.addEventListener('click', function (event) {
            event.preventDefault();
            openLogin();
          });
        });

        // A league game's row, or the next-game card, opens the game's own
        // page on tap (or Enter), except when the tap is on a link or button
        // inside it, such as a team's name or LiveBarn.
        document.querySelectorAll('[data-href]').forEach(function (el) {
          el.addEventListener('click', function (event) {
            if (event.target.closest('a, button')) return;
            location.href = el.dataset.href;
          });
          el.addEventListener('keydown', function (event) {
            if (event.target === el && event.key === 'Enter') location.href = el.dataset.href;
          });
        });

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
        // (Games / All). The Eagles / West choice also works
        // without scripting, through the filter-ours class; the kind filter
        // only exists logged in, which needs scripting anyway. A week shows
        // only while something in it passes both.
        var view = document.querySelector('[data-schedule-view]');
        var whoSelect = document.querySelector('[data-who]');
        var typeButtons = document.querySelectorAll('[data-type-filter]');
        if (view && whoSelect) {
          var who = view.classList.contains('filter-ours') ? 'ours' : 'all';
          var kind = 'all';
          var bar = document.querySelector('[data-period-bar]');
          var today = bar ? bar.dataset.today : iso(new Date());
          // The device's own date, if the page is older than today.
          if (iso(new Date()) > today) today = iso(new Date());
          var allDates = [];
          view.querySelectorAll('.game[data-date]').forEach(function (r) { allDates.push(r.dataset.date); });
          allDates.sort();
          var first = allDates[0] || today, last = allDates[allDates.length - 1] || today;
          if (!period) {
            var savedPeriod = stored(PERIOD_KEY);
            period = /^(day|week|month|season)$/.test(savedPeriod || '') ? savedPeriod : 'week';
          }
          if (!anchor) anchor = today;
          var empty = view.querySelector('[data-sched-empty]');
          // Whose games: 'ours' (the Eagles button), or from the dropdown
          // 'all' (the region) or 'team:<slug>'.
          var oursButton = document.querySelector('[data-filter="ours"]');
          var pick = whoSelect.closest('.team-pick');
          var pickText = pick.querySelector('[data-who-text]');
          var render = function () {
            var r = range(period, anchor);
            var team = who.indexOf('team:') === 0 ? who.slice(5) : '';
            view.classList.toggle('filter-ours', who === 'ours');
            if (oursButton) oursButton.setAttribute('aria-pressed', String(who === 'ours'));
            pick.setAttribute('aria-pressed', String(who !== 'ours'));
            // With the Eagles chosen the dropdown holds no choice, so that
            // picking the region from it still counts as a change.
            if (who === 'ours') whoSelect.selectedIndex = -1; else whoSelect.value = who;
            var chosen = who === 'ours' ? whoSelect.options[0] : whoSelect.options[whoSelect.selectedIndex];
            pickText.textContent = chosen ? chosen.textContent : '';
            typeButtons.forEach(function (b) {
              b.setAttribute('aria-pressed', String(b.dataset.typeFilter === kind));
            });
            var shown = 0;
            view.querySelectorAll('.week').forEach(function (week) {
              var visible = [];
              week.querySelectorAll('.game').forEach(function (row) {
                var d = row.dataset.date;
                var show = (who === 'all' ||
                            (who === 'ours' && row.classList.contains('is-ours')) ||
                            (team && (' ' + (row.dataset.teams || '') + ' ').indexOf(' ' + team + ' ') >= 0)) &&
                           (kind === 'all' || row.dataset.type === kind) &&
                           (!d || (d >= r[0] && d < r[1]));
                row.hidden = !show;
                if (show) visible.push(row);
              });
              week.hidden = !visible.length;
              var count = week.querySelector('.week-count');
              if (count && visible.length) count.textContent = countText(visible);
              shown += visible.length;
            });
            // Today's rows stand out, except in the day view, which is all today.
            view.querySelectorAll('.game[data-date]').forEach(function (row) {
              var mark = row.dataset.date === today && period !== 'day';
              row.classList.toggle('is-today', mark);
              var dayEl = row.querySelector('.game-day');
              if (!dayEl) return;
              if (!dayEl.dataset.day) dayEl.dataset.day = dayEl.textContent;
              dayEl.textContent = mark ? 'Today' : dayEl.dataset.day;
            });
            // Season: a month band where each month starts, since the rows
            // only say the day ("Sat 7").
            var lastMonth = null;
            view.querySelectorAll('.week .game').forEach(function (row) {
              var d = row.dataset.date;
              var starts = period === 'season' && !row.hidden && d && d.slice(0, 7) !== lastMonth;
              row.classList.toggle('month-start', !!starts);
              if (starts) {
                row.dataset.month = MONTHS[+d.slice(5, 7) - 1] + ' ' + d.slice(0, 4);
                lastMonth = d.slice(0, 7);
              }
            });
            var head = view.querySelector('[data-period-head]');
            view.classList.add('by-period');
            if (head) {
              head.hidden = false;
              var r0 = day(r[0]), name, sub;
              if (period === 'day') {
                name = dayTitle(r[0], today);
                // The date beside Today / Tomorrow / Yesterday; a named day has it already.
                sub = name.indexOf(',') < 0 ? label('day', anchor) : '';
              } else if (period === 'week') {
                name = weekTitle(r[0], today);
                sub = label('week', anchor);
              } else if (period === 'month') {
                name = MONTHS[r0.getMonth()];
                sub = String(r0.getFullYear());
              } else {
                name = 'Season';
                sub = (bar ? bar.dataset.season : '').replace(/ Season$/, '');
              }
              var title = head.querySelector('.period-name');
              title.textContent = name;
              title.classList.toggle('now', period !== 'season' && today >= r[0] && today < r[1]);
              head.querySelector('.period-sub').textContent = sub;
              var all = [];
              view.querySelectorAll('.week .game').forEach(function (row) { if (!row.hidden) all.push(row); });
              head.querySelector('.period-count').textContent = all.length ? countText(all) : '';
              var prev = head.querySelector('[data-period-step="-1"]');
              var next = head.querySelector('[data-period-step="1"]');
              prev.hidden = next.hidden = period === 'season';
              prev.disabled = r[0] <= first;
              next.disabled = r[1] > last;
              head.querySelector('[data-period-today]').hidden =
                period === 'season' || (today >= r[0] && today < r[1]);
            }
            if (empty) {
              empty.hidden = shown > 0;
              empty.textContent = 'Nothing scheduled.';
            }
            if (bar) {
              bar.querySelectorAll('[data-period]').forEach(function (b) {
                b.setAttribute('aria-pressed', String(b.dataset.period === period));
              });
            }
          };
          if (bar) {
            bar.querySelectorAll('[data-period]').forEach(function (b) {
              b.addEventListener('click', function () {
                period = b.dataset.period; store(PERIOD_KEY, period); render();
              });
            });
          }
          view.querySelectorAll('[data-period-step]').forEach(function (b) {
            b.addEventListener('click', function () {
              anchor = step(period, anchor, +b.dataset.periodStep); render();
            });
          });
          var todayButton = view.querySelector('[data-period-today]');
          if (todayButton) {
            todayButton.addEventListener('click', function () {
              anchor = today; render();
            });
          }
          var savedWho = stored(FILTER_KEY);
          // Only honour a stored choice the page can actually show.
          if (savedWho === 'all' || (savedWho === 'ours' && view.dataset.hasOurs === '1') ||
              (savedWho && savedWho.indexOf('team:') === 0 &&
               whoSelect.querySelector('option[value="' + savedWho + '"]'))) {
            who = savedWho;
          }
          var savedKind = stored(TYPE_KEY);
          if (typeButtons.length && savedKind === 'game') {
            kind = savedKind;
          }
          render();
          whoSelect.addEventListener('change', function () {
            who = whoSelect.value; store(FILTER_KEY, who); render();
          });
          if (oursButton) {
            oursButton.addEventListener('click', function () {
              who = 'ours'; store(FILTER_KEY, who); render();
            });
          }
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
            .period-pick { display: none; }

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

        /* Under the schedule, on the schedule's own measure, so it lines up
           with the right edge of the games on a wide screen. */
        .schedule + .content-meta {
            max-width: 860px;
            margin-left: auto;
            margin-right: auto;
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


# The header lines up with the content under it. Each page has a measure, the width its content is held to, and on a wide
# screen the brand, the tabs and the season line sit on that page's left and right edges instead of the window's.
_MEASURE_CSS = """
        .container {
            --measure: var(--shell);
            --edge: max(0px, calc((100% - var(--measure)) / 2));
        }

        .container:has(.schedule),
        .container:has(.team-page) {
            --measure: 860px;
        }

        .container:has(.privacy) {
            --measure: 720px;
        }

        .masthead {
            padding-left: max(clamp(12px, 3vw, 24px), var(--edge));
            padding-right: max(clamp(12px, 3vw, 24px), var(--edge));
        }

        /* On a wide screen the brand, the tabs and the season line share one row, to leave the room to the page. The two
           halves are still separate elements, so they are laid out as one with display: contents and ordered here. */
        @media (min-width: 900px) {
            .topbar {
                display: flex;
                align-items: stretch;
                background: var(--surface);
                border-top: 3px solid var(--brand);
                border-bottom: 1px solid var(--line);
                padding: 0 max(clamp(12px, 3vw, 24px), var(--edge));
            }

            .topbar .masthead,
            .topbar .mastnav {
                display: contents;
            }

            .topbar .masthead-brand {
                order: 1;
                align-self: center;
                margin-right: clamp(20px, 3vw, 36px);
                padding: 8px 0;
            }

            .topbar .masthead-wordmark {
                font-size: 1.45rem;
            }

            .topbar .masthead-mark {
                height: 30px;
            }

            .topbar .mastnav a:not(.mastnav-auth) {
                order: 2;
                display: flex;
                align-items: center;
                padding-top: 0;
                padding-bottom: 0;
            }

            .topbar .masthead-meta {
                order: 3;
                margin-left: auto;
                align-self: center;
            }

            .topbar .mastnav a.mastnav-auth {
                order: 4;
                align-self: center;
                margin-left: clamp(16px, 2vw, 28px);
                padding: 0;
            }
        }

        /* The tabs carry their own side padding, so the first label's text lands on the edge. */
        .mastnav {
            padding-left: max(clamp(6px, 2.2vw, 18px), calc(var(--edge) - clamp(11px, 2.2vw, 16px)));
            padding-right: max(clamp(6px, 2.2vw, 18px), calc(var(--edge) - clamp(11px, 2.2vw, 16px)));
        }

        /* The sponsors still scroll the whole width of the band, but fade out at the edges of the content, so the logos
           come and go inside the same column as everything else. */
        @media (min-width: 900px) {
            .sponsor-strip {
                position: relative;
            }

            .sponsor-strip::before,
            .sponsor-strip::after {
                content: "";
                position: absolute;
                top: 0;
                bottom: 0;
                width: calc(var(--edge) + 56px);
                z-index: 1;
                pointer-events: none;
            }

            .sponsor-strip::before {
                left: 0;
                background: linear-gradient(90deg, #ffffff calc(100% - 56px), rgba(255, 255, 255, 0));
            }

            .sponsor-strip::after {
                right: 0;
                background: linear-gradient(270deg, #ffffff calc(100% - 56px), rgba(255, 255, 255, 0));
            }
        }
"""


PAGE_CSS = (_TOKENS_CSS + _BASE_CSS + _LINK_CSS + _MASTHEAD_CSS + _TABLE_CSS
            + _SCHEDULE_CSS + _CHROME_CSS + _SPONSOR_CSS + _RESPONSIVE_CSS + _MEASURE_CSS)

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


# The team pages (generate_team_pages.py): a hero for the team, then blocks
# that share one heading style with the schedule's.
TEAM_CSS = """
        .team-page {
            max-width: 860px;
            margin: 0 auto;
            display: grid;
            gap: 22px;
        }

        .team-back {
            justify-self: start;
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--ink-2);
            text-decoration: none;
            margin-bottom: -10px;
        }

        .team-back:hover {
            color: var(--ink);
        }

        /* --- The team --- */
        .team-hero {
            background: var(--surface);
            border: 1px solid var(--line);
            border-top: 4px solid var(--ink);
            padding: clamp(16px, 4vw, 24px);
            display: grid;
            gap: 18px;
        }

        .team-hero.is-ours {
            border-top-color: var(--brand);
        }

        .team-hero-id {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .team-hero-id .team-logo {
            width: 68px;
            height: 68px;
        }

        .team-hero-id .team-mono {
            font-size: 1.3rem;
        }

        .team-hero-name {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(1.5rem, 5vw, 2.1rem);
            line-height: 1.02;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }

        .team-hero.is-ours .team-hero-name {
            color: var(--brand);
        }

        .team-hero-line {
            margin-top: 6px;
            font-size: 0.86rem;
            color: var(--ink-3);
        }

        .team-hero-numbers {
            display: flex;
            align-items: flex-end;
            flex-wrap: wrap;
            gap: 14px 26px;
            padding-top: 16px;
            border-top: 1px solid var(--line);
        }

        .team-hero-record,
        .hero-stat {
            display: grid;
            gap: 2px;
        }

        .team-hero-record > span:first-child {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(2rem, 7vw, 2.6rem);
            line-height: 1;
            font-variant-numeric: tabular-nums;
        }

        .hero-stat-num {
            font-family: var(--display);
            font-weight: 600;
            font-size: 1.35rem;
            line-height: 1;
            font-variant-numeric: tabular-nums;
        }

        .hero-stat-label {
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
        }

        /* --- Blocks --- */
        .block-head {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 10px;
            padding: 0 2px 8px;
        }

        .block-head h3 {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .block-head span {
            font-size: 0.8rem;
            color: var(--ink-3);
        }

        /* Form: the last five, as chips. */
        .form-row {
            display: flex;
            gap: 8px;
        }

        .form-chip {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            font-family: var(--display);
            font-weight: 600;
            font-size: 1.05rem;
        }

        .form-w {
            background: #e5f4ea;
            color: #0a7a33;
        }

        .form-l {
            background: #fbe9eb;
            color: var(--brand);
        }

        .form-t {
            background: #ebebee;
            color: var(--ink-2);
        }

        /* Scouting: tiles on a hairline grid. */
        /* Two across on a phone, three on a wide screen; the last tile
           stretches to close the row, so no empty cell shows. */
        .scout-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1px;
            background: var(--line);
            border: 1px solid var(--line);
        }

        .scout-tile:last-child:nth-child(odd) {
            grid-column: span 2;
        }

        @media (min-width: 620px) {
            .scout-grid {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }

            .scout-tile:last-child:nth-child(odd) {
                grid-column: auto;
            }

            .scout-tile:last-child:nth-child(3n + 1) {
                grid-column: span 3;
            }

            .scout-tile:last-child:nth-child(3n + 2) {
                grid-column: span 2;
            }
        }

        .scout-tile {
            background: var(--surface);
            padding: 12px 14px;
            display: grid;
            gap: 3px;
            align-content: start;
        }

        .scout-label {
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
        }

        .scout-value {
            font-family: var(--display);
            font-weight: 600;
            font-size: 1.45rem;
            line-height: 1.1;
            font-variant-numeric: tabular-nums;
        }

        .scout-note {
            font-size: 0.76rem;
            color: var(--ink-3);
        }

        /* Points path: points by game against the most possible (dashed). */
        .points-path {
            display: block;
            width: 100%;
            height: 130px;
            background: var(--surface);
            border: 1px solid var(--line);
            padding: 10px;
            box-sizing: border-box;
        }

        .points-path .pace {
            stroke: var(--line);
            stroke-width: 1.5;
            stroke-dasharray: 5 5;
            vector-effect: non-scaling-stroke;
        }

        .points-path .path {
            fill: none;
            stroke: var(--ink);
            stroke-width: 2.5;
            stroke-linejoin: round;
            vector-effect: non-scaling-stroke;
        }

        .points-path .dots line {
            stroke: var(--ink);
            stroke-width: 8;
            stroke-linecap: round;
            vector-effect: non-scaling-stroke;
        }

        .team-page.is-ours .points-path .path {
            stroke: var(--brand);
        }

        .team-page.is-ours .points-path .dots line {
            stroke: var(--brand);
        }

        /* Versus the Eagles. */
        .series {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 6px 16px;
            background: var(--surface);
            border: 1px solid var(--line);
            border-left: 3px solid var(--brand);
            padding: 12px 14px;
            margin-bottom: 10px;
        }

        .series-record {
            display: flex;
            align-items: baseline;
            gap: 10px;
        }

        .series-num {
            font-family: var(--display);
            font-weight: 600;
            font-size: 1.8rem;
            line-height: 1;
            font-variant-numeric: tabular-nums;
        }

        .series-label {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
        }

        .series-next {
            font-size: 0.84rem;
            color: var(--ink-2);
        }

        /* The season-series table has no rank column, so its team column
           pins at the very left. */
        .series-table td.team-name,
        .series-table th.team-col {
            left: 0;
        }

        /* Games, as the schedule shows them, a heading per month. */
        .team-games .week-head {
            padding: 6px 2px 6px;
        }

        .team-games .week-label {
            font-size: 0.8rem;
            color: var(--ink-3);
        }

        .team-games .week-games + .week-head {
            margin-top: 8px;
        }

        .team-empty {
            padding: 24px 12px;
            text-align: center;
            color: var(--ink-3);
            background: var(--surface);
            border: 1px solid var(--line);
        }

"""


# The game pages (generate_game_pages.py), on top of TEAM_CSS.
GAME_CSS = """
        /* --- Team comparisons: goals, shots and penalties, two numbers over a bar --- */
        .compare-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px 28px;
            margin: 16px 0 18px;
        }

        @media (max-width: 700px) {
            .compare-row {
                grid-template-columns: 1fr;
            }
        }

        .compare-head {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: baseline;
            gap: 10px;
        }

        .compare-n {
            font-family: var(--display);
            font-weight: 600;
            font-size: 1.5rem;
            line-height: 1;
            text-align: right;
            font-variant-numeric: tabular-nums;
        }

        .compare-n.us {
            color: var(--brand);
            text-align: left;
        }

        .compare-title {
            display: grid;
            justify-items: center;
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-2);
        }

        .compare-note {
            font-family: var(--body);
            font-weight: 400;
            font-size: 0.68rem;
            letter-spacing: 0.02em;
            text-transform: none;
            color: var(--ink-3);
        }

        .compare-bar {
            display: flex;
            gap: 3px;
            height: 8px;
            margin-top: 8px;
        }

        .compare-bar i {
            display: block;
            border-radius: 4px;
            background: var(--ink);
            opacity: 0.35;
        }

        .compare-bar i.us {
            background: var(--brand);
            opacity: 1;
        }

        /* --- The game sheet as a timeline --- */
        .tl {
            display: grid;
            gap: 7px;
        }

        .tl-period {
            display: grid;
            grid-template-columns: 2.6em 1fr;
            align-items: start;
            gap: 10px;
        }

        .tl-name {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
            line-height: 21px;
        }

        .tl-track {
            position: relative;
            margin: 0 9px;
            min-height: 21px;
        }

        .tl-line {
            position: absolute;
            left: 0;
            right: 0;
            top: 10px;
            height: 2px;
            background: var(--line);
        }

        .tl-tick {
            position: absolute;
            top: 3px;
            bottom: 0;
            border-left: 1px dashed var(--line);
        }

        .tl-axis .tl-track {
            height: 14px;
            min-height: 0;
        }

        .tl-label {
            position: absolute;
            top: 0;
            transform: translateX(-50%);
            font-size: 0.62rem;
            line-height: 1;
            color: var(--ink-3);
            font-variant-numeric: tabular-nums;
        }

        .tl-label:first-child { transform: none; }
        .tl-label.end { left: 100%; transform: translateX(-100%); }

        .tl-dot,
        .tl-to {
            position: absolute;
            top: 11px;
            width: 13px;
            height: 13px;
            margin: -6.5px 0 0 -6.5px;
            border: 2px solid var(--surface);
            box-sizing: border-box;
            background: var(--ink-3);
        }

        .tl-dot {
            border-radius: 50%;
        }

        .tl-to {
            transform: rotate(45deg) scale(0.85);
        }

        .tl-pen {
            position: absolute;
            height: 5px;
            border-radius: 2px;
            background: var(--ink-3);
        }

        /* A bigger target than the mark: a 5 px bar or a 13 px dot is small for a finger. */
        .tl-track .tl-dot::after,
        .tl-track .tl-to::after {
            content: "";
            position: absolute;
            inset: -3px;
        }

        .tl-track .tl-pen::after {
            content: "";
            position: absolute;
            inset: -1px 0;
        }

        .tl-track [data-tip] {
            cursor: default;
            outline: none;
        }

        /* A moment that is on the film opens it. */
        .tl-track a[data-tip] {
            cursor: pointer;
        }

        .tl-track a.tl-dot:hover {
            transform: scale(1.2);
        }

        .tl-track a.tl-to:hover {
            transform: rotate(45deg) scale(1.05);
        }

        .tl-track a.tl-pen:hover {
            opacity: 0.8;
        }

        a.sheet-what.is-film {
            color: inherit;
            text-decoration: none;
            cursor: pointer;
        }

        a.sheet-what.is-film:hover > span:not(.sheet-note) {
            text-decoration: underline;
        }

        .sheet-what .film-icon {
            width: 20px;
            height: 14px;
            flex: none;
            margin-left: auto;
        }

        /* --- Film review: the game's goals and penalties beside the film --- */
        .rv {
            position: fixed;
            inset: 0;
            z-index: 40;
            display: flex;
            flex-direction: column;
            background: var(--surface);
            color: var(--ink);
        }

        .rv-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 8px 12px 8px 18px;
            border-bottom: 1px solid var(--line);
            border-top: 3px solid var(--brand);
            flex: none;
        }

        .rv-title {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .rv-close {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            border: 1px solid var(--line);
            border-radius: 50%;
            background: var(--surface);
            color: var(--ink);
            cursor: pointer;
        }

        .rv-close:hover {
            border-color: var(--ink-3);
        }

        .rv-box {
            flex: 1;
            min-height: 0;
            display: grid;
            grid-template-columns: minmax(280px, 380px) minmax(0, 1fr);
        }

        .rv-list {
            list-style: none;
            overflow-y: auto;
            border-right: 1px solid var(--line);
            padding: 6px 0;
            min-height: 0;
        }

        .rv-row {
            display: grid;
            grid-template-columns: 5.4em 1fr;
            gap: 2px 8px;
            width: 100%;
            padding: 10px 16px 10px 13px;
            border: 0;
            border-left: 3px solid transparent;
            border-bottom: 1px solid var(--line-soft);
            background: transparent;
            color: inherit;
            font: inherit;
            font-size: 0.88rem;
            line-height: 1.35;
            text-align: left;
            cursor: pointer;
        }

        .rv-row:hover {
            background: var(--wash);
        }

        .rv-row.is-now {
            background: var(--crest-wash);
            border-left-color: var(--brand);
        }

        .rv-row.is-now .sheet-when {
            color: var(--brand-dark);
        }

        .rv-close:focus-visible,
        .rv-row:focus-visible,
        .rv-open:focus-visible {
            outline: 2px solid var(--ink);
            outline-offset: -2px;
        }

        .rv-close:focus-visible {
            outline-offset: 2px;
        }

        .rv-stage {
            min-width: 0;
            min-height: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 16px 20px;
            gap: 10px;
            overflow: hidden;
        }

        .rv-frame {
            position: relative;
            width: min(100%, calc((100vh - 170px) * 16 / 9));
            margin: 0 auto;
            aspect-ratio: 16 / 9;
            background: #000000;
        }

        .rv-frame > *,
        .rv-frame iframe {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            border: 0;
        }

        .rv-open {
            align-self: flex-end;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 4px;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--ink-2);
            text-decoration: none;
        }

        .rv-open:hover {
            color: var(--ink);
        }

        .rv-open .film-icon {
            width: 20px;
            height: 14px;
            flex: none;
        }

        .rv-solo {
            grid-template-columns: minmax(0, 1fr);
        }

        @media (max-width: 760px) {
            .rv-box {
                display: flex;
                flex-direction: column;
            }

            .rv-stage {
                order: -1;
                flex: none;
                padding: 0;
                gap: 0;
            }

            .rv-frame {
                width: 100%;
            }

            .rv-open {
                align-self: flex-end;
                padding: 8px 12px;
            }

            .rv-list {
                flex: 1;
                border-right: 0;
                border-top: 1px solid var(--line);
                -webkit-overflow-scrolling: touch;
            }

            .rv-solo .rv-stage {
                order: 0;
                flex: 1;
                justify-content: flex-start;
            }
        }

        @media (prefers-reduced-motion: no-preference) {
            .rv {
                animation: rv-in 0.16s ease-out;
            }

            @keyframes rv-in {
                from { opacity: 0; }
                to { opacity: 1; }
            }
        }

        [data-tip]:focus-visible {
            outline: 2px solid var(--ink);
            outline-offset: 3px;
        }

        .tip {
            display: none;
            position: fixed;
            z-index: 50;
            max-width: 240px;
            padding: 8px 11px;
            background: var(--ink);
            color: #ffffff;
            border-radius: 6px;
            font-size: 0.78rem;
            line-height: 1.4;
            pointer-events: none;
            box-shadow: 0 6px 20px rgba(17, 18, 20, 0.25);
        }

        .tip-logo {
            width: 22px;
            height: 22px;
            object-fit: contain;
            vertical-align: -5px;
            margin-right: 8px;
            padding: 2px;
            border-radius: 4px;
            background: #fff;
        }

        .tip-head {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.86rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 2px;
        }

        .tl-dot.us, .tl-to.us { background: var(--brand); }
        .tl-dot.them, .tl-to.them { background: var(--ink); }
        .tl-pen.us { background: var(--brand); opacity: 0.45; }
        .tl-pen.them { background: var(--ink); opacity: 0.4; }

        .tl-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 4px 16px;
            align-items: center;
            margin-top: 8px;
            font-size: 0.74rem;
            color: var(--ink-3);
        }

        .tl-legend span {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .tl-legend .tl-dot,
        .tl-legend .tl-pen,
        .tl-legend .tl-to {
            position: static;
            display: inline-block;
            margin: 0;
            flex: none;
        }

        .tl-legend .tl-pen {
            width: 22px;
        }

        .tl-legend .tl-to {
            width: 11px;
            height: 11px;
            margin: 0 2px;
        }

        /* --- The league's game sheet --- */
        .sheet-card {
            background: var(--surface);
            border: 1px solid var(--line);
            padding: clamp(12px, 3vw, 18px);
            display: grid;
            gap: 16px;
        }

        .sheet-score {
            width: 100%;
            border-collapse: collapse;
            font-variant-numeric: tabular-nums;
        }

        .sheet-score th,
        .sheet-score td {
            padding: 8px 10px;
            text-align: center;
            border-bottom: 1px solid var(--line-soft);
        }

        .sheet-score th {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
        }

        .sheet-score .sheet-team {
            text-align: left;
            font-weight: 600;
        }

        .sheet-score .sheet-total {
            font-family: var(--display);
            font-size: 1.05rem;
            font-weight: 600;
        }

        .sheet-lists {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 18px;
        }

        .sheet-list h4 {
            font-family: var(--display);
            font-weight: 600;
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--brand);
            margin-bottom: 6px;
        }

        .sheet-list ul {
            list-style: none;
        }

        .sheet-list li {
            display: grid;
            grid-template-columns: 5.4em 1fr;
            gap: 2px 8px;
            padding: 6px 0;
            border-bottom: 1px solid var(--line-soft);
            font-size: 0.88rem;
            line-height: 1.35;
        }

        .sheet-when {
            color: var(--ink-3);
            font-variant-numeric: tabular-nums;
        }

        .sheet-what {
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
        }

        .sheet-score-now {
            margin-left: 6px;
            font-family: var(--display);
            font-weight: 600;
            font-variant-numeric: tabular-nums;
            color: var(--ink-2);
        }

        .sheet-what .team-logo {
            width: 20px;
            height: 20px;
        }

        .sheet-note {
            font-size: 0.78rem;
            color: var(--ink-3);
        }

        /* --- The matchup --- */
        .match-hero {
            background: var(--surface);
            border: 1px solid var(--line);
            border-top: 4px solid var(--ink);
            padding: clamp(14px, 4vw, 22px);
            display: grid;
            gap: 16px;
        }

        .match-hero.is-ours {
            border-top-color: var(--brand);
        }

        .match-top {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 10px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
        }

        .match-status {
            font-family: var(--display);
            font-size: 0.82rem;
            letter-spacing: 0.1em;
            color: var(--ink);
        }

        .match-status.upcoming {
            color: var(--brand);
        }

        .match-face {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
            align-items: center;
            gap: 10px;
        }

        .match-team {
            display: grid;
            justify-items: center;
            text-align: center;
            gap: 3px;
            min-width: 0;
        }

        .match-team .team-logo {
            width: 60px;
            height: 60px;
            margin-bottom: 6px;
        }

        .match-team .team-mono {
            font-size: 1.15rem;
        }

        .match-name {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(0.95rem, 3.6vw, 1.2rem);
            line-height: 1.1;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }

        .match-team.us .match-name {
            color: var(--brand);
        }

        .match-role {
            font-size: 0.66rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--ink-3);
        }

        .match-record {
            font-size: 0.78rem;
            color: var(--ink-3);
        }

        .match-middle {
            display: grid;
            justify-items: center;
            gap: 6px;
        }

        .match-score {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(2.4rem, 11vw, 3.2rem);
            line-height: 1;
            font-variant-numeric: tabular-nums;
            display: flex;
            gap: 8px;
        }

        .match-score .dash {
            color: var(--ink-3);
        }

        .match-score.decided span:not(.win):not(.dash) {
            color: var(--ink-3);
        }

        .match-time {
            display: grid;
            justify-items: center;
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(1.4rem, 6vw, 1.8rem);
            line-height: 1.1;
        }

        .match-date {
            font-family: var(--body);
            font-weight: 500;
            font-size: 0.8rem;
            color: var(--ink-3);
        }

        .match-result {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 3px 9px;
            border-radius: 999px;
        }

        .match-result.result-w {
            background: #e5f4ea;
            color: #0a7a33;
        }

        .match-result.result-l {
            background: #fbe9eb;
            color: var(--brand);
        }

        .match-result.result-t {
            background: #ebebee;
            color: var(--ink-2);
        }

        .match-hero .game-live {
            margin: 0;
        }

        /* --- Watch and go --- */
        .match-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: -8px;
        }

        .match-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 16px;
            border-radius: 999px;
            background: var(--surface);
            border: 1px solid var(--line);
            font-weight: 600;
            font-size: 0.88rem;
            color: var(--ink);
            text-decoration: none;
        }

        .match-btn:hover {
            border-color: var(--ink-3);
        }

        .match-btn img {
            width: 15px;
            height: 17px;
        }

        .match-btn .film-icon {
            width: 20px;
            height: 14px;
            flex: none;
        }

        .match-btn.watch.is-live {
            border-color: var(--brand);
            color: var(--brand);
        }

        /* --- When and where --- */
        .facts {
            background: var(--surface);
            border: 1px solid var(--line);
        }

        .fact {
            display: grid;
            grid-template-columns: 70px minmax(0, 1fr);
            gap: 12px;
            padding: 12px 14px;
            align-items: baseline;
        }

        .fact + .fact {
            border-top: 1px solid var(--line);
        }

        .fact-label {
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
        }

        .fact-value {
            font-size: 0.94rem;
            color: var(--ink);
        }

        .match-place {
            color: inherit;
            text-decoration: underline dotted;
            text-decoration-color: var(--ink-3);
            text-underline-offset: 3px;
        }

        .match-sub {
            display: block;
            margin-top: 2px;
            font-size: 0.8rem;
            color: var(--ink-3);
        }

        /* --- Tale of the tape: the two teams side by side --- */
        .tape {
            background: var(--surface);
            border: 1px solid var(--line);
        }

        .tape-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
            align-items: center;
            gap: 10px;
            padding: 10px 14px;
        }

        .tape-row + .tape-row {
            border-top: 1px solid var(--line);
        }

        .tape-label {
            font-size: 0.66rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
            text-align: center;
        }

        .tape-val {
            font-family: var(--display);
            font-weight: 500;
            font-size: 1.05rem;
            color: var(--ink-2);
            font-variant-numeric: tabular-nums;
        }

        .tape-val.right {
            text-align: right;
        }

        .tape-val.better {
            font-weight: 600;
            color: var(--ink);
        }

        .tape-head .tape-val {
            font-family: var(--body);
            font-weight: 600;
            font-size: 0.86rem;
            color: var(--ink);
        }

        .tape-val.form {
            display: flex;
            gap: 4px;
        }

        .tape-val.form.right {
            justify-content: flex-end;
        }

        .tape .form-chip {
            width: 22px;
            height: 22px;
            font-size: 0.72rem;
        }

        /* The game this page is about, in its season series. */
        .game.is-current {
            background: #eeeef1;
            cursor: default;
        }

        .game.is-current .game-when::after {
            content: "This game";
            display: block;
            margin-top: 3px;
            font-size: 0.6rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-3);
        }
"""


# Team-event pages (generate_event_pages.py), on top of TEAM_CSS and GAME_CSS.
# Each kind has its own accent on the top bar and label.
EVENT_CSS = """
        .event-body {
            display: grid;
            gap: 22px;
        }

        .event-hero.kind-practice {
            border-top-color: #2f6fb3;
        }

        .event-hero.kind-dryland {
            border-top-color: #e07b1a;
        }

        .event-hero.kind-tournament {
            border-top-color: #c9a227;
        }

        .event-hero.kind-game {
            border-top-color: var(--brand);
        }

        .event-hero.kind-practice .match-top > span:first-child {
            color: #2f6fb3;
        }

        .event-hero.kind-dryland .match-top > span:first-child {
            color: #c4650f;
        }

        .event-hero.kind-tournament .match-top > span:first-child {
            color: #a8841a;
        }

        .event-hero.kind-game .match-top > span:first-child {
            color: var(--brand);
        }

        .match-status.live {
            color: var(--brand);
        }

        .event-name {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(1.8rem, 8vw, 2.6rem);
            line-height: 1;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }

        .event-when {
            margin-top: 8px;
            font-size: 0.95rem;
            color: var(--ink-2);
        }

        .event-actions {
            margin-top: 10px;
        }

        .swatch {
            display: inline-block;
            width: 0.8em;
            height: 0.8em;
            margin-right: 7px;
            border-radius: 50%;
            box-shadow: inset 0 0 0 1px rgba(20, 22, 26, 0.25);
            vertical-align: 0.02em;
        }

        .event-locked {
            background: var(--surface);
            border: 1px solid var(--line);
            border-top: 4px solid var(--ink);
            padding: 24px 18px;
            display: grid;
            gap: 10px;
            justify-items: start;
        }

        .event-locked h2 {
            font-family: var(--display);
            font-weight: 600;
            font-size: 1.4rem;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }

        .event-locked p {
            color: var(--ink-2);
            font-size: 0.92rem;
            margin-bottom: 6px;
        }
"""

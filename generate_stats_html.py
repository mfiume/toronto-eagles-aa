#!/usr/bin/env python3
"""
The Statistics tab: team-level numbers for the Eagles from the league's game sheets.

Only the team is measured: no player appears in the sheets, and none appears here. The numbers are for the team,
so the page is sealed with the team password (team_crypto.py) exactly as the team events are. The public page holds
a short locked notice and the ciphertext; the figures are written into the page only in encrypted form, and the
browser decrypts them once a parent logs in (page_common.SCHEDULE_JS).

`compute` is pure (sheets and shots in, numbers out) so the tests can check every figure without building a page.
"""

import html
import json
import os

import config
import page_common
import team_crypto
from generate_game_pages import SHEETS_FILE, clock_seconds, load_shots, penalty_name
from generate_schedule_html import LOGIN_DIALOG

PASSWORD_ENV = "TEAM_EVENTS_PASSWORD"
PAGE = "statistics.html"

PERIOD_SECONDS = 12 * 60
# Two penalties called at the same stoppage cancel each other out: neither team plays shorthanded.
OFFSET_WINDOW = 5
MINOR = 120
# A ten minute misconduct sends the player off but does not leave the team a skater down.
MISCONDUCT = 10


def load_sheets():
    try:
        with open(SHEETS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def elapsed(period, clock):
    """Seconds into the game. The sheet's clock counts down from the period's start."""
    return (period - 1) * PERIOD_SECONDS + (PERIOD_SECONDS - clock_seconds(clock))


def opposite(side):
    return "away" if side == "home" else "home"


def special_teams(penalties, goals, side):
    """
    The power play of `side`: how many chances it had and how many of them it scored on.

    A chance is a minor or a major taken by the other team that is not cancelled by a penalty the same length at the
    same stoppage. A goal is a power-play goal when it is scored inside such a penalty, and a minor ends with it.
    """
    other = opposite(side)
    taken = [{"side": p["side"], "start": elapsed(p["period"], p["clock"]), "length": int(p["minutes"]) * 60}
             for p in penalties if int(p["minutes"]) < MISCONDUCT]
    cancelled = set()
    for i, p in enumerate(taken):
        if i in cancelled:
            continue
        for j, q in enumerate(taken):
            if j != i and j not in cancelled and q["side"] != p["side"] and q["length"] == p["length"] \
                    and abs(q["start"] - p["start"]) <= OFFSET_WINDOW:
                cancelled.update((i, j))
                break
    chances = [{"start": p["start"], "end": p["start"] + p["length"], "minor": p["length"] == MINOR}
               for i, p in enumerate(taken) if i not in cancelled and p["side"] == other]
    scored = 0
    for t in sorted(elapsed(g["period"], g["clock"]) for g in goals if g["side"] == side):
        live = [c for c in chances if c["start"] <= t < c["end"]]
        if live:
            scored += 1
            minors = [c for c in live if c["minor"]]
            if minors:
                min(minors, key=lambda c: c["end"])["end"] = t
    return len(chances), scored


def result_of(gf, ga):
    return "W" if gf > ga else "L" if gf < ga else "T"


def record_line(record):
    return f'{record["W"]}-{record["L"]}-{record["T"]}'


def compute(sheets, shots, team=None):
    """Team figures across every game sheet the Eagles played in. Empty when there are none."""
    team = team or config.TEAM_NAME
    games, periods_for, periods_against = [], {}, {}
    pens_by_period = {"taken": {}, "drawn": {}}
    names = {"taken": {}, "drawn": {}}
    pp_chances = pp_goals = pk_chances = pk_allowed = 0
    shot_games = shots_for = shots_against = goals_in_shot_games_for = goals_in_shot_games_against = 0
    flow = {k: {"W": 0, "L": 0, "T": 0} for k in ("first", "behind", "lead1", "lead2", "trail1", "trail2", "close")}
    record = {"W": 0, "L": 0, "T": 0}
    pim = 0
    for gid in sorted(sheets):
        g = sheets[gid]
        if team not in (g.get("home"), g.get("away")):
            continue
        us = "home" if g["home"] == team else "away"
        them = opposite(us)
        gf, ga = g["final"][us], g["final"][them]
        res = result_of(gf, ga)
        record[res] += 1
        by_period = {x["period"]: x for x in g["periods"]}
        for n, x in by_period.items():
            periods_for[n] = periods_for.get(n, 0) + x[us]
            periods_against[n] = periods_against.get(n, 0) + x[them]
        taken = [p for p in g["penalties"] if p["side"] == us]
        drawn = [p for p in g["penalties"] if p["side"] == them]
        for kind, rows in (("taken", taken), ("drawn", drawn)):
            for p in rows:
                pens_by_period[kind][p["period"]] = pens_by_period[kind].get(p["period"], 0) + 1
                label = penalty_name(p["code"]) or "Penalty"
                names[kind][label] = names[kind].get(label, 0) + 1
        game_pim = sum(int(p["minutes"]) for p in taken)
        pim += game_pim
        chances, scored = special_teams(g["penalties"], g["goals"], us)
        pp_chances += chances
        pp_goals += scored
        against, allowed = special_teams(g["penalties"], g["goals"], them)
        pk_chances += against
        pk_allowed += allowed
        s = shots.get(gid)
        if s:
            shot_games += 1
            shots_for += s["eagles"]
            shots_against += s["opponent"]
            goals_in_shot_games_for += gf
            goals_in_shot_games_against += ga
        ordered = sorted(g["goals"], key=lambda x: (x["period"], -clock_seconds(x["clock"])))
        if ordered:
            flow["first" if ordered[0]["side"] == us else "behind"][res] += 1
        running = {1: [0, 0], 2: [0, 0]}
        for n in (1, 2):
            ahead = sum(by_period[k][us] for k in by_period if k <= n)
            behind = sum(by_period[k][them] for k in by_period if k <= n)
            running[n] = [ahead, behind]
            if ahead > behind:
                flow[f"lead{n}"][res] += 1
            elif ahead < behind:
                flow[f"trail{n}"][res] += 1
        if abs(gf - ga) <= 1:
            flow["close"][res] += 1
        games.append({"id": gid, "date": gid[:10], "opponent": g["away"] if us == "home" else g["home"],
                      "place": "home" if us == "home" else "away", "gf": gf, "ga": ga, "result": res,
                      "shots": (s["eagles"], s["opponent"]) if s else None,
                      "taken": len(taken), "drawn": len(drawn), "pim": game_pim})
    n = len(games)
    if not n:
        return None
    gf_total = sum(x["gf"] for x in games)
    ga_total = sum(x["ga"] for x in games)
    pct = lambda a, b: round(100 * a / b) if b else None
    return {
        "games": n, "record": record, "gf": gf_total, "ga": ga_total, "pim": pim,
        "periods": sorted(set(periods_for) | set(periods_against)),
        "periods_for": periods_for, "periods_against": periods_against,
        "pens_by_period": pens_by_period, "names": names,
        "pp": {"chances": pp_chances, "goals": pp_goals, "pct": pct(pp_goals, pp_chances)},
        "pk": {"chances": pk_chances, "allowed": pk_allowed, "pct": pct(pk_chances - pk_allowed, pk_chances)},
        "shots": ({"games": shot_games, "for": shots_for, "against": shots_against,
                   "shooting": round(100 * goals_in_shot_games_for / shots_for, 1) if shots_for else None,
                   "saves": round(100 * (1 - goals_in_shot_games_against / shots_against), 1) if shots_against else None}
                  if shot_games else None),
        "flow": flow, "list": games,
    }


# --- The page ---------------------------------------------------------------------------------------------------

def avg(total, games):
    return f"{total / games:.1f}"


def period_name(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, "Overtime" if n == 4 else f"OT{n - 3}")


def bar_pair(rows, games, ours_label, theirs_label):
    """Grouped bars, one row per label: ours in red over theirs in grey, scaled together by the per-game figure."""
    top = max([max(a, b) for _, a, b in rows] + [1]) / games
    out = ""
    for label, a, b in rows:
        out += (f'<div class="stat-row"><span class="stat-label">{html.escape(label)}</span><div class="stat-bars">'
                f'<div class="stat-line"><i class="us" style="width:{100 * (a / games) / top:.0f}%"></i>'
                f'<b>{avg(a, games)}</b><span>{a}</span></div>'
                f'<div class="stat-line"><i style="width:{100 * (b / games) / top:.0f}%"></i>'
                f'<b>{avg(b, games)}</b><span>{b}</span></div></div></div>')
    return (f'<div class="stat-key"><span class="us">{html.escape(ours_label)}</span>'
            f'<span>{html.escape(theirs_label)}</span><em>Per game, with the total</em></div>{out}')


def ranked(counts, empty):
    if not counts:
        return f'<p class="team-empty">{empty}</p>'
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    top = items[0][1]
    return '<div class="stat-rank">' + "".join(
        f'<div class="stat-rank-row"><span>{html.escape(name)}</span><b>{n}</b>'
        f'<i style="width:{100 * n / top:.0f}%"></i></div>' for name, n in items) + "</div>"


def tile(label, value, note=""):
    return (f'<div class="stat-tile"><span class="stat-tile-label">{html.escape(label)}</span>'
            f'<span class="stat-tile-value">{value}</span>'
            f'{f"<span class=stat-tile-note>{note}</span>" if note else ""}</div>')


def pct_text(pct):
    return "–" if pct is None else f"{pct}%"


def flow_row(label, record):
    """Our record in the games that went this way. A situation that has not come up yet is left out."""
    if not sum(record.values()):
        return ""
    return (f'<div class="fact"><span class="fact-label">{html.escape(label)}</span>'
            f'<span class="fact-value">{record_line(record)}</span></div>')


def block(title, body, meta=""):
    return (f'<section class="team-block"><div class="block-head"><h3>{html.escape(title)}</h3>'
            f'{f"<span>{html.escape(meta)}</span>" if meta else ""}</div>{body}</section>')


def body(stats):
    """The statistics as the signed-in viewer sees them."""
    if not stats:
        return ('<section class="team-block"><div class="block-head"><h3>Team statistics</h3></div>'
                '<p class="team-empty">Statistics appear after the first game sheet.</p></section>')
    n = stats["games"]
    games_text = f"{n} game" + ("" if n == 1 else "s")
    parts = ['<div class="stat-tiles">'
             + tile("Record", record_line(stats["record"]), games_text)
             + tile("Goals for", avg(stats["gf"], n), f'{stats["gf"]} in total')
             + tile("Goals against", avg(stats["ga"], n), f'{stats["ga"]} in total')
             + tile("Penalty minutes", avg(stats["pim"], n), "Per game")
             + "</div>"]
    rows = [(period_name(p), stats["periods_for"].get(p, 0), stats["periods_against"].get(p, 0)) for p in stats["periods"]]
    parts.append(block("Goals by period", bar_pair(rows, n, "Eagles", "Opponent")))
    rows = [(period_name(p), stats["pens_by_period"]["taken"].get(p, 0), stats["pens_by_period"]["drawn"].get(p, 0))
            for p in stats["periods"]]
    parts.append(block("Penalties by period", bar_pair(rows, n, "We take", "We draw")))
    parts.append('<div class="stat-pair">'
                 + block("Penalties we take", ranked(stats["names"]["taken"], "No penalties yet."))
                 + block("Penalties we draw", ranked(stats["names"]["drawn"], "No penalties yet.")) + "</div>")
    pp, pk = stats["pp"], stats["pk"]
    parts.append(block("Special teams", '<div class="stat-tiles two">'
                       + tile("Power play", pct_text(pp["pct"]), f'{pp["goals"]} goals on {pp["chances"]} chances')
                       + tile("Penalty kill", pct_text(pk["pct"]),
                              f'{pk["allowed"]} goals against on {pk["chances"]} chances') + "</div>"))
    if stats["shots"]:
        s = stats["shots"]
        sg = s["games"]
        parts.append(block("Shots", '<div class="stat-tiles">'
                           + tile("Shots for", avg(s["for"], sg), "Per game")
                           + tile("Shots against", avg(s["against"], sg), "Per game")
                           + tile("Shooting", pct_text(s["shooting"] and round(s["shooting"])), "Goals per shot")
                           + tile("Saves", pct_text(s["saves"] and round(s["saves"])), "Shots stopped") + "</div>",
                           f"{sg} game" + ("" if sg == 1 else "s")))
    f = stats["flow"]
    parts.append(block("Game flow", '<div class="facts stat-flow">'
                       + flow_row("We scored first", f["first"]) + flow_row("Opponent scored first", f["behind"])
                       + flow_row("Led after 1st", f["lead1"]) + flow_row("Trailed after 1st", f["trail1"])
                       + flow_row("Led after 2nd", f["lead2"]) + flow_row("Trailed after 2nd", f["trail2"])
                       + flow_row("One goal games", f["close"]) + "</div>", "Our record in each"))
    rows = ""
    for g in stats["list"]:
        shots = "–" if not g["shots"] else "{}–{}".format(*g["shots"])
        rows += (f'<tr><td>{g["date"][5:].replace("-", "/")}</td><td>{html.escape(g["opponent"])}</td>'
                 f'<td class="r-{g["result"]}">{g["result"]} {g["gf"]}–{g["ga"]}</td>'
                 f'<td>{shots}</td><td>{g["taken"]}–{g["drawn"]}</td><td>{g["pim"]}</td></tr>')
    parts.append(block("Game by game", '<div class="stat-table"><table><thead><tr><th>Date</th><th>Opponent</th>'
                       '<th>Result</th><th>Shots</th><th>Penalties</th><th>Minutes</th></tr></thead>'
                       f"<tbody>{rows}</tbody></table></div>"))
    return "".join(parts)


LOCKED = """
                <section class="team-block event-locked">
                    <h2>Team statistics</h2>
                    <p>Statistics are for the team. Log in with the team password to see them.</p>
                    <a class="match-btn" href="#login" data-open-login>Team Login</a>
                </section>
"""

STATS_CSS = """
        .team-page, .event-body, .team-block { min-width: 0; }
        .stat-tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 22px; }
        .stat-tiles.two { grid-template-columns: repeat(2, 1fr); }
        .team-block .stat-tiles { margin-bottom: 0; }
        .stat-flow .fact { grid-template-columns: 11em minmax(0, 1fr); }
        .stat-tile { background: var(--surface); border: 1px solid var(--line); padding: 12px 14px; display: grid; gap: 4px; }
        .stat-tile-label { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-3); }
        .stat-tile-value { font-family: var(--display); font-weight: 600; font-size: 1.9rem; line-height: 1; font-variant-numeric: tabular-nums; }
        .stat-tile-note { font-size: 0.8rem; color: var(--ink-3); }
        .stat-key { display: flex; gap: 16px; align-items: baseline; font-size: 0.78rem; color: var(--ink-2); padding: 0 2px 8px; }
        .stat-key span::before { content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 6px; border-radius: 3px; background: var(--ink); opacity: 0.35; }
        .stat-key span.us::before { background: var(--brand); opacity: 1; }
        .stat-key em { margin-left: auto; font-style: normal; color: var(--ink-3); }
        .stat-row { display: grid; grid-template-columns: 4.5em 1fr; gap: 10px; align-items: center; padding: 8px 14px; background: var(--surface); border: 1px solid var(--line); border-top: 0; }
        .stat-key + .stat-row { border-top: 1px solid var(--line); }
        .stat-label { font-family: var(--display); font-weight: 600; font-size: 0.9rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink-2); }
        .stat-bars { display: grid; gap: 4px; }
        .stat-line { display: grid; grid-template-columns: minmax(0, 1fr) 2.6em 2.2em; gap: 8px; align-items: center; }
        .stat-line i { display: block; height: 8px; border-radius: 4px; background: var(--ink); opacity: 0.35; min-width: 2px; }
        .stat-line i.us { background: var(--brand); opacity: 1; }
        .stat-line b { font-family: var(--display); font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }
        .stat-line span { font-size: 0.78rem; color: var(--ink-3); font-variant-numeric: tabular-nums; }
        .stat-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 0 24px; }
        .stat-rank { background: var(--surface); border: 1px solid var(--line); }
        .stat-rank-row { position: relative; display: flex; justify-content: space-between; gap: 10px; padding: 10px 14px; font-size: 0.94rem; }
        .stat-rank-row + .stat-rank-row { border-top: 1px solid var(--line); }
        .stat-rank-row b { font-family: var(--display); font-variant-numeric: tabular-nums; }
        .stat-rank-row i { position: absolute; left: 0; bottom: 0; height: 3px; background: var(--brand); opacity: 0.8; }
        .stat-table { background: var(--surface); border: 1px solid var(--line); overflow-x: auto; }
        .stat-table table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        .stat-table th, .stat-table td { padding: 10px 14px; text-align: left; white-space: nowrap; font-variant-numeric: tabular-nums; }
        .stat-table th { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-3); border-bottom: 1px solid var(--line); }
        .stat-table tr + tr td { border-top: 1px solid var(--line-soft); }
        .stat-table .r-W { color: var(--brand); font-weight: 600; }
        .team-block + .team-block, .stat-pair + .team-block, .team-block + .stat-pair { margin-top: 22px; }
        @media (max-width: 700px) {
            .stat-tiles { grid-template-columns: repeat(2, 1fr); }
            .stat-pair { grid-template-columns: 1fr; }
            .stat-key { flex-wrap: wrap; }
            .stat-key em { margin-left: 0; width: 100%; }
        }
"""


def page(sealed, timestamp):
    payload = json.dumps(sealed).replace("</", "<\\/")
    dialog = LOGIN_DIALOG.replace("to see practices, dryland and team events", "to see the team statistics")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Statistics - {config.SITE_TITLE}</title>
    <meta name="robots" content="noindex">
{page_common.FONT_LINK}
{page_common.FAVICON_LINKS}
    <style>
{page_common.PAGE_CSS}{page_common.TEAM_CSS}{page_common.GAME_CSS}{page_common.EVENT_CSS}{STATS_CSS}    </style>
</head>
<body>
    <div class="container">
{page_common.masthead(PAGE, page_common.division_label(), page_common.season_label())}

        <div class="content">
            <div class="team-page">
                <div class="event-body" data-schedule-block>{LOCKED}</div>
            </div>
{page_common.freshness(timestamp)}            <script type="application/json" id="team-events">{payload}</script>
{dialog}        </div>

{page_common.page_end()}    </div>
{page_common.SCHEDULE_JS}</body>
</html>
"""


def generate(timestamp=None):
    password = os.environ.get(PASSWORD_ENV, "")
    if not password:
        print("Statistics page skipped: no team password")
        return []
    stats = compute(load_sheets(), load_shots())
    if timestamp is None:
        try:
            with open("schedule.json", encoding="utf-8") as f:
                timestamp = json.load(f).get("timestamp", "")
        except (FileNotFoundError, ValueError):
            timestamp = ""
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(page(team_crypto.Sealer(password).seal(body(stats)), timestamp))
    # Counts only: the log of a public repository is public.
    print(f"Generated the statistics page from {stats['games'] if stats else 0} game sheets")
    return [PAGE]


if __name__ == "__main__":
    generate()

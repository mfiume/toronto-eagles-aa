#!/usr/bin/env python3
"""
The standings order, by the GTHL's rules: points, then the tie-breaking
procedure of GTHL Regulation 12.2.

GTHL league schedules are balanced, so the balanced-schedule procedures apply:

12.2(c), two teams level on points:
  (i)   most wins;
  (ii)  most wins against each other;
  (iii) goals for / (goals for + goals against), over all games;
  (iv)  first goal in their season series;
  (v)   a one-game playoff.

12.2(d), three or more teams level on points:
  (i)   most wins;
  (ii)  goals for / (goals for + goals against), in games between the tied
        teams;
  the team that comes out on top takes the highest place, and the process
  starts again with the rest (12.2(c) once two remain).

Where the published data cannot settle it (who scored first is not
published; a playoff game or a coin toss is not played until the end of the
season, per 12.2(b) for first place and the last playoff spot), the teams
share the place and are shown as tied.

When three or more teams are level and only some of them share the most
wins, the procedure is applied again to just those teams to find which of
them is placed highest; the regulation does not spell this case out.
"""

import json
import os

import season_schedule


def record(row):
    """(wins, losses, ties) from a standings row's W-L-T, zeros when blank."""
    try:
        w, l, t = (int(n) for n in str(row.get("W-L-T", "")).split("-"))
        return w, l, t
    except ValueError:
        return 0, 0, 0


def points(row):
    try:
        return int(row.get("PTS") or 0)
    except ValueError:
        return 0


def ratio(gf, ga):
    """Goals for / (for + against); None when no goals at all, which cannot rank."""
    return gf / (gf + ga) if gf + ga else None


def season_goals(row):
    """A team's season goals for and against, from its per-game averages."""
    try:
        gp = int(row.get("GP") or 0)
        return round(float(row.get("GFA")) * gp), round(float(row.get("GAA")) * gp)
    except (TypeError, ValueError):
        return 0, 0


def load_results(path=None):
    """Every played league game as (away, home, away goals, home goals)."""
    path = path or season_schedule.SEASON_FILE
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        games = json.load(f).get("games", [])
    return [(g["away"], g["home"], g["score"]["away"], g["score"]["home"])
            for g in games
            if g.get("score") and g.get("status") == "final" and g.get("type", "LG") in ("LG", "")]


class Ranker:
    def __init__(self, standings, results):
        self.rows = {r["Team"]: r for r in standings}
        self.results = results

    def wins(self, team):
        return record(self.rows[team])[0]

    def wins_against(self, team, others):
        return sum(1 for a, h, ga, gh in self.results
                   if (a == team and h in others and ga > gh) or (h == team and a in others and gh > ga))

    def ratio_among(self, team, group):
        """Goal ratio in games between `team` and the rest of `group`."""
        gf = ga = 0
        for a, h, sa, sh in self.results:
            if a == team and h in group:
                gf, ga = gf + sa, ga + sh
            elif h == team and a in group:
                gf, ga = gf + sh, ga + sa
        return ratio(gf, ga)

    @staticmethod
    def leaders(teams, key):
        """The teams with the best value of `key`; all of them if it cannot be compared."""
        values = {t: key(t) for t in teams}
        if any(v is None for v in values.values()):
            return list(teams)
        best = max(values.values())
        return [t for t in teams if values[t] == best]

    def two(self, a, b):
        """12.2(c): [[higher], [lower]], or [[a, b]] if still level."""
        for key in (self.wins,
                    lambda t: self.wins_against(t, {b if t == a else a}),
                    lambda t: ratio(*season_goals(self.rows[t]))):
            top = self.leaders([a, b], key)
            if len(top) == 1:
                return [top, [b if top[0] == a else a]]
        return [[a, b]]

    def top_group(self, teams):
        """The team placed highest among `teams`, or the teams that share that place."""
        if len(teams) == 1:
            return list(teams)
        if len(teams) == 2:
            return self.two(*teams)[0]
        most = self.leaders(teams, self.wins)
        if len(most) < len(teams):
            return self.top_group(most)
        group = set(teams)
        best = self.leaders(teams, lambda t: self.ratio_among(t, group - {t}))
        return best   # More than one: settled only by a coin toss, so they share it.

    def order(self, teams):
        """`teams`, all level on points, as places: a list of groups."""
        places, rest = [], list(teams)
        while rest:
            top = self.top_group(rest)
            places.append(top)
            rest = [t for t in rest if t not in top]
        return places


def rank(standings, results=None):
    """
    The standings in GTHL order. Position counts 1, 2, 3...; Rank is the place
    shown, shared by teams the rules cannot separate, with Tied set on them.
    """
    results = load_results() if results is None else results
    ranker = Ranker(standings, results)
    by_gthl = sorted(standings, key=lambda r: r.get("Position", 0))
    groups = {}
    for r in by_gthl:
        groups.setdefault(points(r), []).append(r["Team"])
    out, position = [], 1
    for pts in sorted(groups, reverse=True):
        for place in ranker.order(groups[pts]):
            for team in place:
                out.append(dict(ranker.rows[team], Position=len(out) + 1, Rank=position,
                                Tied=len(place) > 1))
            position += len(place)
    return out

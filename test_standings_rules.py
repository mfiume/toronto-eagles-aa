#!/usr/bin/env python3
"""Unit tests for the GTHL tie-breaking rules (Regulation 12.2). No files."""

import unittest

import standings_rules as sr


def row(team, wlt, gp=None, gfa="", gaa="", pos=0):
    w, l, t = (int(n) for n in wlt.split("-"))
    gp = gp if gp is not None else w + l + t
    return {"Team": team, "W-L-T": wlt, "GP": str(gp), "PTS": str(2 * w + t),
            "GFA": gfa, "GAA": gaa, "Position": pos}


def places(standings, results):
    return [(r["Rank"], r["Tied"], r["Team"]) for r in sr.rank(standings, results)]


class TwoTeams(unittest.TestCase):
    def test_most_wins_first(self):
        # Both on 4 points: A from two wins, B from a win and two ties.
        out = places([row("B", "1-0-2", pos=1), row("A", "2-1-0", pos=2)], [])
        self.assertEqual(out, [(1, False, "A"), (2, False, "B")])

    def test_then_wins_against_each_other(self):
        out = places([row("A", "1-1-0", pos=1), row("B", "1-1-0", pos=2)],
                     [("A", "B", 1, 3), ("B", "C", 0, 2), ("A", "C", 5, 0)])
        self.assertEqual(out[0][2], "B")

    def test_then_goal_ratio_over_all_games(self):
        out = places([row("A", "1-0-1", gfa="2.00", gaa="2.00", pos=1),
                      row("B", "1-0-1", gfa="3.00", gaa="1.00", pos=2)],
                     [("A", "B", 2, 2)])
        self.assertEqual(out, [(1, False, "B"), (2, False, "A")])

    def test_level_on_everything_is_tied(self):
        out = places([row("A", "0-0-1", gfa="4.00", gaa="4.00", pos=1),
                      row("B", "0-0-1", gfa="4.00", gaa="4.00", pos=2)],
                     [("A", "B", 4, 4)])
        self.assertEqual(out, [(1, True, "A"), (1, True, "B")])


class ThreeOrMore(unittest.TestCase):
    def test_most_wins_takes_the_top_then_two_team_rules(self):
        standings = [row("A", "1-0-2", pos=1), row("B", "2-1-0", pos=2), row("C", "1-0-2", pos=3)]
        out = places(standings, [("A", "C", 1, 3)])
        self.assertEqual(out[0][2], "B")
        # A and C: equal wins, C has the win against A.
        self.assertEqual([t for _, _, t in out[1:]], ["C", "A"])

    def test_goal_ratio_among_the_tied_teams(self):
        standings = [row(t, "1-1-0", pos=i) for i, t in enumerate("ABC")]
        results = [("A", "B", 1, 0), ("B", "C", 1, 0), ("C", "A", 5, 0)]
        out = places(standings, results)
        # Among the three: C 5-1, B 1-1, A 1-5, so C is placed highest. Then
        # A and B go to the two-team rules, where A's win over B decides it.
        self.assertEqual([t for _, _, t in out], ["C", "A", "B"])

    def test_teams_yet_to_play_share_the_place(self):
        standings = [row("A", "1-0-0", pos=1), row("B", "0-1-0", pos=2),
                     row("C", "0-0-0", pos=3), row("D", "0-0-0", pos=4)]
        out = places(standings, [("A", "B", 3, 1)])
        self.assertEqual(out[0], (1, False, "A"))
        self.assertEqual({(r, tied) for r, tied, _ in out[1:]}, {(2, True)})


if __name__ == "__main__":
    unittest.main()

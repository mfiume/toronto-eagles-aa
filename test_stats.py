#!/usr/bin/env python3
"""The statistics page: every figure on synthetic game sheets, and that none of it is readable without the team password."""

import os
import re
import unittest
from unittest import mock

import config
import generate_stats_html as stats
import page_common
import team_crypto

US = config.TEAM_NAME


def sheet(home, away, final, periods, goals=(), penalties=()):
    return {"home": home, "away": away, "final": {"home": final[0], "away": final[1]},
            "periods": [{"period": i + 1, "home": h, "away": a} for i, (h, a) in enumerate(periods)],
            "goals": [{"period": p, "clock": c, "side": s, "kind": ""} for p, c, s in goals],
            "penalties": [{"period": p, "clock": c, "side": s, "code": code, "minutes": m} for p, c, s, code, m in penalties],
            "timeouts": []}


class SpecialTeams(unittest.TestCase):
    def test_goal_inside_an_opponent_minor_is_a_power_play_goal(self):
        pens = [(1, "8:00", "away", "TR", 2)]
        goals = [(1, "7:30", "home")]
        self.assertEqual(stats.special_teams(*self.split(pens, goals), "home"), (1, 1))

    def test_goal_after_the_penalty_ran_out_is_not(self):
        pens = [(1, "8:00", "away", "TR", 2)]
        goals = [(1, "5:30", "home")]
        self.assertEqual(stats.special_teams(*self.split(pens, goals), "home"), (1, 0))

    def test_a_power_play_goal_ends_a_minor(self):
        pens = [(1, "8:00", "away", "TR", 2)]
        goals = [(1, "7:40", "home"), (1, "7:20", "home")]
        self.assertEqual(stats.special_teams(*self.split(pens, goals), "home"), (1, 1))

    def test_a_major_is_not_ended_by_a_goal(self):
        pens = [(1, "8:00", "away", "BC", 5)]
        goals = [(1, "7:40", "home"), (1, "7:20", "home")]
        self.assertEqual(stats.special_teams(*self.split(pens, goals), "home"), (1, 2))

    def test_penalties_called_together_cancel(self):
        pens = [(1, "6:31", "home", "BC", 2), (1, "6:31", "away", "HKG", 2)]
        goals = [(1, "6:00", "home")]
        self.assertEqual(stats.special_teams(*self.split(pens, goals), "home"), (0, 0))

    def test_a_misconduct_gives_no_chance(self):
        pens = [(1, "8:00", "away", "8.6(b)", 10)]
        goals = [(1, "7:30", "home")]
        self.assertEqual(stats.special_teams(*self.split(pens, goals), "home"), (0, 0))

    def test_a_penalty_runs_into_the_next_period(self):
        pens = [(1, "0:40", "away", "SL", 2)]
        goals = [(2, "11:30", "home")]
        self.assertEqual(stats.special_teams(*self.split(pens, goals), "home"), (1, 1))

    @staticmethod
    def split(pens, goals):
        p = [{"period": a, "clock": b, "side": c, "code": d, "minutes": e} for a, b, c, d, e in pens]
        g = [{"period": a, "clock": b, "side": c} for a, b, c in goals]
        return p, g


class Compute(unittest.TestCase):
    def setUp(self):
        self.sheets = {
            "2026-10-01_a_at_b": sheet(US, "Rivals", (3, 1), [(1, 0), (2, 1), (0, 0)],
                                       goals=[(1, "5:00", "home"), (1, "3:00", "home"), (2, "6:00", "away"), (2, "1:00", "home")],
                                       penalties=[(1, "9:00", "home", "TR", 2), (2, "8:00", "away", "SL", 2)]),
            "2026-10-02_c_at_d": sheet("Rivals", US, (2, 2), [(1, 0), (0, 2), (1, 0)],
                                       goals=[(1, "4:00", "home"), (2, "6:00", "away"), (2, "3:00", "away"), (3, "2:00", "home")]),
            "2026-10-03_e_at_f": sheet("Other", "Rivals", (5, 1), [(5, 1)]),
        }
        self.shots = {"2026-10-01_a_at_b": {"eagles": 20, "opponent": 10}}
        self.s = stats.compute(self.sheets, self.shots)

    def test_only_games_the_team_played_count(self):
        self.assertEqual(self.s["games"], 2)

    def test_record_and_goals_follow_the_team_not_the_side(self):
        self.assertEqual(self.s["record"], {"W": 1, "L": 0, "T": 1})
        self.assertEqual((self.s["gf"], self.s["ga"]), (5, 3))

    def test_goals_by_period(self):
        self.assertEqual(self.s["periods_for"], {1: 1, 2: 4, 3: 0})
        self.assertEqual(self.s["periods_against"], {1: 1, 2: 1, 3: 1})

    def test_penalties_are_named_in_words_and_split_taken_and_drawn(self):
        self.assertEqual(self.s["names"]["taken"], {"Tripping": 1})
        self.assertEqual(self.s["names"]["drawn"], {"Slashing": 1})
        self.assertEqual(self.s["pim"], 2)

    def test_shots_count_only_the_games_that_have_them(self):
        shots = self.s["shots"]
        self.assertEqual((shots["games"], shots["for"], shots["against"]), (1, 20, 10))
        self.assertEqual(shots["shooting"], 15.0)
        self.assertEqual(shots["saves"], 90.0)

    def test_scoring_first_and_leading_after_a_period(self):
        self.assertEqual(self.s["flow"]["first"], {"W": 1, "L": 0, "T": 0})
        self.assertEqual(self.s["flow"]["behind"], {"W": 0, "L": 0, "T": 1})
        self.assertEqual(self.s["flow"]["lead1"], {"W": 1, "L": 0, "T": 0})

    def test_no_games_is_none_and_the_page_says_so(self):
        self.assertIsNone(stats.compute({}, {}))
        self.assertIn("Statistics appear after the first game sheet", stats.body(None))

    def test_nothing_in_the_page_names_a_player(self):
        text = stats.body(self.s)
        self.assertNotRegex(text, r"(?i)player|goalie|#\d+")


class Gate(unittest.TestCase):
    def setUp(self):
        self.s = stats.compute({"2026-10-01_a_at_b": sheet(US, "Rivals", (3, 1), [(3, 1)])}, {})
        self.body = stats.body(self.s)

    def test_the_public_page_holds_no_figure_and_the_password_opens_it(self):
        sealed = team_crypto.Sealer("correct horse").seal(self.body)
        with mock.patch.dict(os.environ, {"TEAM_EVENTS_PASSWORD": "correct horse"}):
            html = stats.page(sealed, "")
        for visible in ("Goals by period", "Penalties by period", "Rivals", "Record"):
            self.assertNotIn(visible, html.split('id="team-events"')[0].split("<body>")[1])
        self.assertNotIn("Rivals", html)
        self.assertEqual(team_crypto.decrypt(sealed, "correct horse"), self.body)
        with self.assertRaises(Exception):
            team_crypto.decrypt(sealed, "wrong password")

    def test_no_password_builds_no_page(self):
        with mock.patch.dict(os.environ, {"TEAM_EVENTS_PASSWORD": ""}), \
                mock.patch("builtins.open", side_effect=AssertionError("must not write")):
            self.assertEqual(stats.generate(), [])

    def test_the_tab_exists_only_with_a_team_password(self):
        with mock.patch.dict(os.environ, {"TEAM_EVENTS_PASSWORD": "x"}):
            self.assertIn("statistics.html", page_common.masthead("index.html", "", ""))
        with mock.patch.dict(os.environ, {"TEAM_EVENTS_PASSWORD": ""}):
            self.assertNotIn("statistics.html", page_common.masthead("index.html", "", ""))

    def test_the_copy_has_no_em_dash(self):
        self.assertNotIn("—", self.body + stats.LOCKED + stats.STATS_CSS)


if __name__ == "__main__":
    unittest.main()

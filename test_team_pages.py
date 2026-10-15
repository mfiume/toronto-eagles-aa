#!/usr/bin/env python3
"""Unit tests for the team pages' arithmetic. No network, no files."""

import unittest
from datetime import date, datetime

import generate_team_pages as tp


def game(day, away, home, score=":"):
    return {"row": {"Away": away, "Home": home, "Score": score, "Date": "", "Time": ""},
            "day": day, "start": datetime.combine(day, datetime.min.time()),
            "score": tp.parse_score(tp.format_score(score))}


GAMES = [
    game(date(2026, 10, 1), "Toronto Eagles", "Mississauga Beast", "2:3"),
    game(date(2026, 10, 8), "Mississauga Beast", "Toronto Eagles", "1:4"),
    game(date(2026, 10, 15), "Mississauga Beast", "Vaughan Rangers", "0:0"),
    game(date(2026, 11, 1), "Toronto Eagles", "Mississauga Beast"),
]


class SideOf(unittest.TestCase):
    def test_goals_and_result_from_each_side(self):
        s = tp.side_of(GAMES[0], "Mississauga Beast")
        self.assertEqual((s["opponent"], s["home"], s["gf"], s["ga"], s["result"]),
                         ("Toronto Eagles", True, 3, 2, "W"))
        self.assertEqual(tp.side_of(GAMES[1], "Toronto Eagles")["result"], "W")

    def test_unplayed_game_has_no_result(self):
        self.assertNotIn("result", tp.side_of(GAMES[3], "Toronto Eagles"))


class Sections(unittest.TestCase):
    def test_series_record_is_the_eagles(self):
        html = tp.versus_eagles(GAMES, "Mississauga Beast", datetime(2026, 10, 20, tzinfo=tp.page_common.TORONTO), date(2026, 10, 20))
        self.assertIn("1-1-0", html)
        self.assertIn("3 meetings", html)

    def test_form_oldest_first(self):
        played = [g for g in tp.team_games(GAMES, "Mississauga Beast") if g["score"]]
        html = tp.form(played, "Mississauga Beast")
        self.assertLess(html.index("form-w"), html.index("form-l"))
        self.assertIn("form-t", html)

    def test_no_points_path_before_two_games(self):
        self.assertEqual(tp.points_path(GAMES[:1], "Toronto Eagles"), "")

    def test_page_name(self):
        self.assertEqual(tp.page_name("The Attack"), "team-the-attack.html")


if __name__ == "__main__":
    unittest.main()

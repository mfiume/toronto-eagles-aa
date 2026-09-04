#!/usr/bin/env python3
"""
Unit tests for the season schedule accumulator. No network, no browser.

The behaviour worth protecting is that a game never disappears once seen, and
that its id survives the things that legitimately change about a fixture.
"""

import unittest

import season_schedule as ss


def row(date="18-Oct-2026 Sun", time="1:10 PM", away="West Mall Lightning",
        home="Toronto Eagles", score=":", arena="Lambton"):
    return {"Date": date, "Time": time, "Away": away, "Score": score,
            "Home": home, "Arena": arena, "Region": "",
            "Div/Cat": "Under 11 / AA", "Type": "LG"}


WINDOW = {"from_date": "27-Aug-2026", "to_date": "02-Dec-2026"}


class TestParsing(unittest.TestCase):
    def test_iso_date(self):
        self.assertEqual(ss.iso_date("12-Oct-2026 Mon"), "2026-10-12")
        self.assertEqual(ss.iso_date("2-Jan-2027 Sat"), "2027-01-02")
        self.assertEqual(ss.iso_date("garbage"), "")

    def test_iso_time(self):
        self.assertEqual(ss.iso_time("7:10 PM"), "19:10")
        self.assertEqual(ss.iso_time("11:10 AM"), "11:10")
        self.assertEqual(ss.iso_time("12:30 AM"), "00:30")
        self.assertEqual(ss.iso_time("12:30 PM"), "12:30")
        self.assertEqual(ss.iso_time(""), "")

    def test_unplayed_game_has_no_score(self):
        self.assertIsNone(ss.parse_score(":"))
        self.assertIsNone(ss.parse_score(""))
        self.assertEqual(ss.parse_score("4:2"), {"away": 4, "home": 2})


class TestGameId(unittest.TestCase):
    def test_id_shape(self):
        self.assertEqual(
            ss.game_id(row()),
            "2026-10-18_west-mall-lightning_at_toronto-eagles")

    def test_id_survives_a_time_change(self):
        """Ice times slide constantly; that must not orphan a tracked game."""
        self.assertEqual(ss.game_id(row(time="1:10 PM")),
                         ss.game_id(row(time="1:30 PM")))

    def test_id_changes_when_the_date_moves(self):
        """A fixture moved to another day really is a different fixture."""
        self.assertNotEqual(ss.game_id(row()),
                            ss.game_id(row(date="19-Oct-2026 Mon")))

    def test_home_and_away_are_not_interchangeable(self):
        self.assertNotEqual(
            ss.game_id(row()),
            ss.game_id(row(away="Toronto Eagles", home="West Mall Lightning")))


class TestEnrich(unittest.TestCase):
    def test_our_home_game(self):
        game = ss.enrich(row())
        self.assertTrue(game["is_eagles"])
        self.assertEqual(game["eagles_side"], "home")
        self.assertEqual(game["opponent"], "West Mall Lightning")
        self.assertEqual(game["status"], "scheduled")
        self.assertIsNone(game["result"])

    def test_someone_elses_game(self):
        game = ss.enrich(row(away="Vaughan Panthers", home="Duffield Devils"))
        self.assertFalse(game["is_eagles"])
        self.assertIsNone(game["eagles_side"])
        self.assertIsNone(game["opponent"])

    def test_result_is_from_our_perspective(self):
        won_at_home = ss.enrich(row(score="2:5"))
        self.assertEqual(won_at_home["result"], "W")
        lost_at_home = ss.enrich(row(score="5:2"))
        self.assertEqual(lost_at_home["result"], "L")
        away = ss.enrich(row(away="Toronto Eagles", home="Duffield Devils",
                             score="5:2"))
        self.assertEqual(away["result"], "W")
        self.assertEqual(ss.enrich(row(score="3:3"))["result"], "T")
        self.assertEqual(ss.enrich(row(score="3:3"))["status"], "final")


class TestMerge(unittest.TestCase):
    def test_a_game_that_ages_out_of_the_window_is_kept(self):
        """The whole reason this file exists."""
        first = ss.merge([row(date="05-Sep-2026 Sat")], WINDOW, existing={})
        keyed = {g["id"]: g for g in first}

        # A later scrape whose window has moved past that game entirely.
        later = ss.merge([row(date="18-Oct-2026 Sun")],
                         {"from_date": "01-Oct-2026", "to_date": "31-Dec-2026"},
                         existing=keyed)

        self.assertEqual(len(later), 2)
        self.assertIn("2026-09-05_west-mall-lightning_at_toronto-eagles",
                      {g["id"] for g in later})

    def test_a_final_score_updates_in_place(self):
        first = ss.merge([row()], WINDOW, existing={})
        keyed = {g["id"]: g for g in first}
        second = ss.merge([row(score="2:5")], WINDOW, existing=keyed)

        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["status"], "final")
        self.assertEqual(second[0]["result"], "W")
        self.assertEqual(second[0]["first_seen"], first[0]["first_seen"])
        self.assertNotEqual(second[0]["last_seen"], first[0]["last_seen"])

    def test_a_game_delisted_inside_the_window_is_flagged_not_deleted(self):
        first = ss.merge([row(), row(date="19-Oct-2026 Mon")], WINDOW, existing={})
        keyed = {g["id"]: g for g in first}
        second = ss.merge([row()], WINDOW, existing=keyed)

        by_id = {g["id"]: g for g in second}
        self.assertEqual(len(second), 2)
        gone = by_id["2026-10-19_west-mall-lightning_at_toronto-eagles"]
        self.assertEqual(gone["status"], "not_listed")
        self.assertIn("missing_since", gone)
        self.assertEqual(by_id[ss.game_id(row())]["status"], "scheduled")

    def test_a_game_outside_the_window_is_not_flagged(self):
        first = ss.merge([row(date="05-Sep-2026 Sat")], WINDOW, existing={})
        keyed = {g["id"]: g for g in first}
        second = ss.merge([], {"from_date": "01-Oct-2026", "to_date": "31-Dec-2026"},
                          existing=keyed)
        self.assertEqual(second[0]["status"], "scheduled")

    def test_a_delisted_game_that_comes_back_is_unflagged(self):
        first = ss.merge([row()], WINDOW, existing={})
        keyed = {g["id"]: g for g in first}
        keyed = {g["id"]: g for g in ss.merge([], WINDOW, existing=keyed)}
        self.assertEqual(keyed[ss.game_id(row())]["status"], "not_listed")

        back = ss.merge([row()], WINDOW, existing=keyed)
        self.assertEqual(back[0]["status"], "scheduled")

    def test_games_come_back_in_date_and_time_order(self):
        games = ss.merge([row(date="19-Oct-2026 Mon"),
                          row(time="9:00 AM", away="Vaughan Rangers"),
                          row()], WINDOW, existing={})
        self.assertEqual([(g["date"], g["time"]) for g in games],
                         [("2026-10-18", "09:00"),
                          ("2026-10-18", "13:10"),
                          ("2026-10-19", "13:10")])

    def test_the_same_matchup_twice_in_a_day_is_a_collision_we_warn_about(self):
        """
        Date-plus-teams ids cannot tell a doubleheader apart. That never happens
        in league play, but it must not fail silently if it ever does.
        """
        games = ss.merge([row(time="9:00 AM"), row(time="1:10 PM")],
                         WINDOW, existing={})
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["time"], "13:10")

    def test_an_unparseable_date_is_skipped_rather_than_keyed_as_empty(self):
        games = ss.merge([row(date="who knows"), row()], WINDOW, existing={})
        self.assertEqual(len(games), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""The film moments on the game sheet: parsing the secret, what the page exposes, and what is sealed. No network."""

import json
import os
import unittest

import generate_game_pages as gp
import generate_schedule_html as gs
import team_crypto

SHEET = {
    "home": "Mississauga Jets", "away": "Toronto Eagles", "final": {"home": 1, "away": 2},
    "periods": [{"period": 1, "home": 1, "away": 1}, {"period": 2, "home": 0, "away": 1}],
    "goals": [{"period": 1, "clock": "11:45", "side": "home", "kind": ""}, {"period": 1, "clock": "3:16", "side": "away", "kind": ""},
              {"period": 2, "clock": "4:33", "side": "away", "kind": ""}],
    "penalties": [{"period": 1, "clock": "7:10", "side": "away", "code": "TR", "minutes": 2}],
    "timeouts": [{"period": 2, "clock": "9:00", "side": "home"}],
}
URL = "https://youtu.be/FIXTUREID1"
SECRET = {"g1": {"url": URL, "moments": [{"kind": "goal", "period": 1, "clock": "3:16", "t": 755}]}, "g2": "https://youtu.be/PLAINID2"}


def load(raw):
    old = os.environ.get("GAME_VIDEOS")
    os.environ["GAME_VIDEOS"] = raw
    try:
        return gs.load_film()
    finally:
        if old is None:
            del os.environ["GAME_VIDEOS"]
        else:
            os.environ["GAME_VIDEOS"] = old


class Secret(unittest.TestCase):
    def test_reads_both_forms(self):
        films = load(json.dumps(SECRET))
        self.assertEqual(films["g1"]["moments"], [{"kind": "goal", "period": 1, "clock": "3:16", "t": 755}])
        self.assertEqual(films["g2"], {"url": "https://youtu.be/PLAINID2", "moments": []})

    def test_load_videos_still_gives_addresses(self):
        old = os.environ.get("GAME_VIDEOS")
        os.environ["GAME_VIDEOS"] = json.dumps(SECRET)
        try:
            self.assertEqual(gs.load_videos(), {"g1": URL, "g2": "https://youtu.be/PLAINID2"})
        finally:
            if old is None:
                del os.environ["GAME_VIDEOS"]
            else:
                os.environ["GAME_VIDEOS"] = old

    def test_drops_what_is_not_an_address_or_a_well_formed_moment(self):
        films = load(json.dumps({"a": "http://x", "b": 5, "c": {"url": URL, "moments": [
            {"kind": "goal", "period": 1, "clock": "3:16", "t": -1}, {"kind": "shot", "period": 1, "clock": "3:16", "t": 5},
            {"kind": "goal", "period": 1, "clock": "bad", "t": 5}, {"kind": "goal"}, {"kind": "goal", "period": 2, "clock": "0:59", "t": 9}]}}))
        self.assertEqual(list(films), ["c"])
        self.assertEqual(films["c"]["moments"], [{"kind": "goal", "period": 2, "clock": "0:59", "t": 9}])

    def test_bad_secret_is_nothing(self):
        self.assertEqual(load("not json"), {})
        self.assertEqual(load("[1]"), {})


class Page(unittest.TestCase):
    def test_every_mark_and_row_names_its_moment(self):
        html = gp.sheet_timeline(SHEET) + gp.game_sheet(SHEET)
        for key in ("goal|1|11:45", "goal|1|3:16", "goal|2|4:33", "penalty|1|7:10", "timeout|2|9:00"):
            self.assertGreaterEqual(html.count(f'data-m="{key}"'), 2, key)

    def test_sealed_package_holds_the_moments_and_the_page_holds_no_address(self):
        sealed = team_crypto.Sealer("pw").seal(gp.film_package(load(json.dumps(SECRET))["g1"]))
        page = gp.film_payload(sealed) + gp.sheet_timeline(SHEET) + gp.game_sheet(SHEET)
        self.assertNotIn("youtu", page)
        self.assertNotIn("FIXTUREID1", page)
        inner = json.loads(team_crypto.decrypt(sealed, "pw"))
        self.assertEqual(inner["url"], URL)
        self.assertEqual(inner["moments"], SECRET["g1"]["moments"])
        self.assertIn("Video review", inner["html"])

    def test_no_film_adds_nothing(self):
        self.assertEqual(gp.film_payload(None), "")


if __name__ == "__main__":
    unittest.main()

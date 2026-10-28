#!/usr/bin/env python3
"""
The in-page film review: what the public page carries, what is sealed, and a fixture game page for the browser check.
No network, and no real video address: the fixture's video id is made up.

  python3 test_film_review.py                    run the unit tests
  python3 test_film_review.py --fixture DIR      write the fixture pages for check_film_review.mjs into DIR
"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest

import generate_game_pages as gp
import page_common
import team_crypto

PASSWORD = "fixture-password"
WITH_MOMENTS = "2026-10-22_toronto-eagles_at_mississauga-jets"
PLAIN = "2026-10-25_the-attack_at_toronto-eagles"
VIDEO_ID = "FAKEID00001"
# The last penalty of the game (3rd period, 1:53) has no placed time on purpose.
MOMENTS = [
    {"kind": "goal", "period": 1, "clock": "11:45", "t": 100},
    {"kind": "penalty", "period": 1, "clock": "7:10", "t": 300},
    {"kind": "goal", "period": 1, "clock": "3:16", "t": 755},
    {"kind": "penalty", "period": 2, "clock": "11:46", "t": 1000},
    {"kind": "goal", "period": 2, "clock": "4:33", "t": 1400},
    {"kind": "penalty", "period": 2, "clock": "4:02", "t": 1420},
    {"kind": "goal", "period": 3, "clock": "9:35", "t": 2000},
    {"kind": "penalty", "period": 3, "clock": "7:28", "t": 2200},
    {"kind": "goal", "period": 3, "clock": "4:16", "t": 2500},
]
# The Eagles are the away team of this game: the Jets score first, then the Eagles score four. The 755 s goal is only known to within 40 s either way.
SCORE = {"steps": [{"t": 120, "us": 0, "them": 1},
                   {"t": 775, "us": 1, "them": 1, "approx": True, "hw": 40},
                   {"t": 1420, "us": 2, "them": 1},
                   {"t": 2020, "us": 3, "them": 1},
                   {"t": 2520, "us": 4, "them": 1}],
         "periods": [{"p": 2, "t": 1000}, {"p": 3, "t": 1900}], "end": 3000}
SECRET = {WITH_MOMENTS: {"url": f"https://youtu.be/{VIDEO_ID}", "moments": MOMENTS, "lead": 20, "score": SCORE}, PLAIN: f"https://youtu.be/{VIDEO_ID}"}


def write_fixture(out):
    """Generate the game pages from the real schedule and sheets, with a made-up film for two games, into `out`."""
    here = os.path.dirname(os.path.abspath(__file__))
    work = tempfile.mkdtemp()
    for name in ("standings.json", "schedule.json", "game_sheets.json", "game_shots.json", "team_scores.json"):
        if os.path.exists(os.path.join(here, name)):
            shutil.copy(os.path.join(here, name), work)
    # Long names for the layout check: two real penalty names and one far longer than any code the league uses.
    sheets = json.load(open(os.path.join(work, "game_sheets.json")))
    sheets[WITH_MOMENTS]["penalties"] += [
        {"clock": "1:20", "code": "INTGT", "minutes": 2, "period": 3, "side": "home"},
        {"clock": "1:10", "code": "RAW", "minutes": 2, "period": 3, "side": "away"},
        {"clock": "0:40", "code": "Unsportsmanlike conduct and misconduct", "minutes": 10, "period": 3, "side": "home"}]
    sheets[WITH_MOMENTS]["timeouts"] = [{"clock": "4:53", "period": 3, "side": "home"}, {"clock": "2:05", "period": 3, "side": "away"}]
    json.dump(sheets, open(os.path.join(work, "game_sheets.json"), "w"))
    os.symlink(os.path.join(here, "assets"), os.path.join(work, "assets"))
    old = os.getcwd(), os.environ.get("GAME_VIDEOS"), os.environ.get("TEAM_EVENTS_PASSWORD")
    os.chdir(work)
    os.environ["GAME_VIDEOS"], os.environ["TEAM_EVENTS_PASSWORD"] = json.dumps(SECRET), PASSWORD
    try:
        gp.generate()
    finally:
        os.chdir(old[0])
        for k, v in zip(("GAME_VIDEOS", "TEAM_EVENTS_PASSWORD"), old[1:]):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    os.makedirs(out, exist_ok=True)
    for name in os.listdir(work):
        if name.startswith("game-") and name.endswith(".html"):
            shutil.copy(os.path.join(work, name), out)
    shutil.copytree(os.path.join(here, "assets"), os.path.join(out, "assets"), dirs_exist_ok=True)
    shutil.rmtree(work)
    return {"moments": f"game-{WITH_MOMENTS}.html", "plain": f"game-{PLAIN}.html", "password": PASSWORD, "id": VIDEO_ID}


class Review(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.mkdtemp()
        cls.info = write_fixture(cls.out)
        cls.page = open(os.path.join(cls.out, cls.info["moments"]), encoding="utf-8").read()
        cls.plain = open(os.path.join(cls.out, cls.info["plain"]), encoding="utf-8").read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out)

    def test_public_page_names_no_video_host_or_id(self):
        for page in (self.page, self.plain):
            self.assertNotIn("youtu", page)
            self.assertNotIn("iframe_api", page)
            self.assertNotIn(VIDEO_ID, page)

    def test_player_script_address_is_sealed_with_the_film(self):
        sealed = json.loads(re.search(r'id="game-film">(.*?)</script>', self.page, re.S).group(1).replace("<\\/", "</"))
        inner = json.loads(team_crypto.decrypt(sealed, PASSWORD))
        self.assertEqual(inner["api"], "https://www.youtube.com/iframe_api")
        self.assertEqual(inner["moments"], MOMENTS)

    def test_nothing_is_fetched_before_the_review_is_opened(self):
        js = page_common.REVIEW_JS
        self.assertNotIn("youtu", js)
        self.assertNotIn("youtu", page_common.FILM_JS)
        self.assertEqual(js.count("createElement('script')"), 1)
        self.assertLess(js.index("function show("), js.index("createElement('script')"))

    def test_player_settings(self):
        js = page_common.REVIEW_JS
        for part in ("rel: 0", "modestbranding: 1", "playsinline: 1", "autoplay: 1", "start:", "seekTo(", "playVideo()", "getCurrentTime()", "500"):
            self.assertIn(part, js)
        self.assertNotIn("setPlaybackQuality", js)

    def sealed(self, page):
        s = json.loads(re.search(r'id="game-film">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))
        return json.loads(team_crypto.decrypt(s, PASSWORD))

    def test_package_carries_the_game_info(self):
        info = self.sealed(self.plain)["info"]
        self.assertEqual(info["away"], "The Attack")
        self.assertEqual(info["home"], "Toronto Eagles")
        self.assertEqual(info["score"], "3\u20133")
        self.assertEqual(info["when"], "Sunday, October 25 \u00b7 12:10 PM \u00b7 Lambton Arena")

    def test_package_without_info_is_still_valid(self):
        entry = {"url": f"https://youtu.be/{VIDEO_ID}", "moments": []}
        self.assertNotIn("info", json.loads(gp.film_package(entry)))
        self.assertIn("'Video review'", page_common.REVIEW_JS)

    def test_rows_carry_no_play_icon(self):
        self.assertNotIn("insertAdjacentHTML('beforeend', ICON)", page_common.FILM_JS.split("function review")[0])

    def test_hash_scheme_and_share_in_the_script(self):
        js = page_common.REVIEW_JS
        for part in ("history.replaceState", "'#review='", "Copy link", "Link copied", "navigator.clipboard"):
            self.assertIn(part, js)
        self.assertNotIn("pushState", js)

    def test_package_carries_the_lead_in(self):
        self.assertEqual(self.sealed(self.page)["lead"], 20)
        self.assertEqual(json.loads(gp.film_package({"url": f"https://youtu.be/{VIDEO_ID}", "moments": [], "lead": 15}))["lead"], 15)
        self.assertIn("film.lead", page_common.REVIEW_JS)

    def test_filters_highlights_and_countdown_in_the_script(self):
        js = page_common.REVIEW_JS
        for part in ("'goals-for'", "'goals-against'", "'penalties'", "CLIP_AFTER", "COUNTDOWN_AFTER", "&filter=", "#review=highlights", "highlights", "role', 'radiogroup'"):
            self.assertIn(part, js.replace("'highlights'", "highlights"))

    def test_sheet_rows_say_whose_event_they_are(self):
        self.assertEqual(self.page.count('data-side="us"') + self.page.count('data-side="them"'), self.page.count('<li data-m="goal') + self.page.count('<li data-m="penalty') + self.page.count('<li data-m="timeout'))
        self.assertIn('data-side="us"', self.page)

    def test_package_carries_the_score_line_and_the_public_page_does_not(self):
        inner = self.sealed(self.page)
        self.assertEqual(inner["score"], SCORE)
        self.assertNotIn("score", self.sealed(self.plain))
        for page in (self.page, self.plain):
            self.assertNotIn('"approx"', page)
            self.assertNotIn('"hw"', page)
            self.assertNotIn('"steps"', page)
            self.assertNotIn('"us":', page)
            self.assertNotIn('"them":', page)
            self.assertNotIn('"periods"', page)

    def test_package_carries_the_teams_for_the_score_strip(self):
        info = self.sealed(self.page)["info"]
        self.assertEqual((info["us"], info["them"]), ("Toronto Eagles", "Mississauga Jets"))
        self.assertTrue(info["usLogo"].startswith("assets/logos/"))
        info = self.sealed(self.plain)["info"]
        self.assertEqual((info["us"], info["them"]), ("Toronto Eagles", "The Attack"))

    def test_no_em_dash_in_the_review(self):
        self.assertNotIn("\u2014", page_common.REVIEW_JS)
        self.assertNotIn("\u2014", page_common.FILM_JS)

class ScoreLine(unittest.TestCase):
    """What the site accepts of the score line Film Room sends: all of it or none of it."""

    def load(self, value):
        old = os.environ.get("GAME_VIDEOS")
        os.environ["GAME_VIDEOS"] = json.dumps({"g": value})
        try:
            return gp.load_film().get("g")
        finally:
            if old is None:
                os.environ.pop("GAME_VIDEOS", None)
            else:
                os.environ["GAME_VIDEOS"] = old

    def test_the_older_forms_have_no_score_and_no_lead(self):
        self.assertEqual(self.load("https://youtu.be/x"), {"url": "https://youtu.be/x", "moments": []})
        self.assertEqual(self.load({"url": "https://youtu.be/x", "moments": []}), {"url": "https://youtu.be/x", "moments": []})

    def test_lead_and_score_pass_through(self):
        film = self.load({"url": "https://youtu.be/x", "moments": [], "lead": 20, "score": SCORE})
        self.assertEqual(film["lead"], 20)
        self.assertEqual(film["score"], SCORE)
        self.assertEqual(json.loads(gp.film_package(film))["score"], SCORE)

    def test_a_malformed_score_line_is_dropped_whole(self):
        step = lambda t, us, them: {"t": t, "us": us, "them": them}
        bad = [
            "x", {}, {"steps": []}, {"steps": "x"},
            {"steps": [step(10, 0, 2)]},                      # two goals at once
            {"steps": [step(10, 1, 0), step(5, 1, 1)]},        # out of order
            {"steps": [step(10, 1, 0), step(20, 0, 1)]},       # the score went down
            {"steps": [step(10, 1, 0), step(20, 1, 0)]},       # no goal
            {"steps": [step(-1, 1, 0)]},
            {"steps": [{"t": "10", "us": 1, "them": 0}]},
        ]
        for score in bad:
            self.assertNotIn("score", self.load({"url": "https://youtu.be/x", "moments": [], "score": score}), score)
        self.assertNotIn("lead", self.load({"url": "https://youtu.be/x", "moments": [], "lead": -5}))
        self.assertNotIn("lead", self.load({"url": "https://youtu.be/x", "moments": [], "lead": "20"}))

    def test_periods_and_end_are_kept_when_valid_and_ignored_when_not(self):
        film = self.load({"url": "https://youtu.be/x", "moments": [], "score": {"steps": [{"t": 1, "us": 1, "them": 0}], "periods": [{"p": 3, "t": 9}, {"p": 2, "t": 5}, {"p": 1, "t": 0}, {"p": "2", "t": 1}], "end": "x"}})
        self.assertEqual(film["score"], {"steps": [{"t": 1, "us": 1, "them": 0}], "periods": [{"p": 2, "t": 5}, {"p": 3, "t": 9}]})


class EventLinks(unittest.TestCase):
    def test_each_event_row_has_its_own_copy_link(self):
        import page_common
        self.assertIn("rv-row-link", page_common.FILM_JS)
        self.assertIn("'#review=' + ev.key", page_common.FILM_JS)


if __name__ == "__main__":
    if "--fixture" in sys.argv:
        print(json.dumps(write_fixture(sys.argv[sys.argv.index("--fixture") + 1])))
    else:
        unittest.main()

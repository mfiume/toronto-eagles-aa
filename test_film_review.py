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
    {"kind": "penalty", "period": 2, "clock": "4:02", "t": 1450},
    {"kind": "goal", "period": 3, "clock": "9:35", "t": 2000},
    {"kind": "penalty", "period": 3, "clock": "7:28", "t": 2200},
    {"kind": "goal", "period": 3, "clock": "4:16", "t": 2500},
]
SECRET = {WITH_MOMENTS: {"url": f"https://youtu.be/{VIDEO_ID}", "moments": MOMENTS}, PLAIN: f"https://youtu.be/{VIDEO_ID}"}


def write_fixture(out):
    """Generate the game pages from the real schedule and sheets, with a made-up film for two games, into `out`."""
    here = os.path.dirname(os.path.abspath(__file__))
    work = tempfile.mkdtemp()
    for name in ("standings.json", "schedule.json", "game_sheets.json", "game_shots.json", "team_scores.json"):
        if os.path.exists(os.path.join(here, name)):
            shutil.copy(os.path.join(here, name), work)
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

    def test_no_em_dash_in_the_review(self):
        self.assertNotIn("—", page_common.REVIEW_JS)


if __name__ == "__main__":
    if "--fixture" in sys.argv:
        print(json.dumps(write_fixture(sys.argv[sys.argv.index("--fixture") + 1])))
    else:
        unittest.main()

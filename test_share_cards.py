"""The picture and words a shared link shows: every card exists at the size link previews want, the tags name them with absolute addresses, and quotes in a title cannot break the tag."""
import re
import struct
import unittest
from datetime import date

import config
import generate_game_pages as gp
import page_common


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


class Cards(unittest.TestCase):
    def test_every_card_is_1200_by_630(self):
        for name in page_common.SHARE_CARDS:
            self.assertEqual(png_size(f"assets/share/{name}.png"), (1200, 630), name)

    def test_tags_give_absolute_addresses_and_the_large_card(self):
        tags = page_common.share_tags("schedule", "Schedule", "Games and results.", "schedule.html")
        self.assertIn(f'content="{config.SITE_URL}assets/share/schedule.png"', tags)
        self.assertIn(f'property="og:url" content="{config.SITE_URL}schedule.html"', tags)
        self.assertIn('name="twitter:card" content="summary_large_image"', tags)
        self.assertIn('property="og:image:width" content="1200"', tags)
        self.assertTrue(config.SITE_URL.startswith("https://"))

    def test_a_quote_in_a_name_stays_inside_its_tag(self):
        tags = page_common.share_tags("game", 'The "Ice" <Hawks>', "O'Brien & sons", "x.html")
        self.assertNotIn('<Hawks>', tags)
        for line in tags.splitlines():
            self.assertEqual(line.count("<meta"), 1)
            self.assertTrue(line.rstrip().endswith(">"))

    def test_an_unknown_card_is_refused(self):
        with self.assertRaises(AssertionError):
            page_common.share_tags("nope", "t", "d")

    def test_no_em_dash_in_the_words(self):
        self.assertNotIn("—", page_common.share_tags("site", "T", "D"))


class GameLine(unittest.TestCase):
    row = {"Away": "Mississauga Beast", "Home": "Toronto Eagles", "Time": "7:00 PM", "Arena": "Lambton Arena"}

    def test_a_final_game_names_the_score(self):
        line = gp.share_line({"row": self.row, "day": date(2026, 11, 1), "score": {"away": 3, "home": 2}})
        self.assertRegex(line, r"^Final: Mississauga Beast 3, Toronto Eagles 2\. Sunday, November 1")

    def test_a_game_to_come_names_when_and_where(self):
        line = gp.share_line({"row": self.row, "day": date(2026, 11, 20), "score": None})
        self.assertRegex(line, r"^Friday, November 20 · 7:00 PM")


if __name__ == "__main__":
    unittest.main()

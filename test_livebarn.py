#!/usr/bin/env python3
"""Unit tests for LiveBarn links on team-calendar games. No network, no files."""

import unittest
from datetime import datetime

import livebarn

KNOWN = {"Lambton": "4198", "Scotiabank Pond 2": "4088", "Scotiabank Pond 3": "4089",
         "Iceland 4": "4217"}


class Learn(unittest.TestCase):
    def test_pads_come_from_the_gthl_links(self):
        rows = [{"Arena": "Lambton", "Stream": "https://livebarn.com/en/video/4198/2026-10-18/13:10"},
                {"Arena": "Tomken 2", "Stream": ""}]
        games = [{"arena": "Iceland 4", "stream": "https://livebarn.com/en/video/4217/2026-10-22/18:40"}]
        self.assertEqual(livebarn.learn(rows, games, {"Westwood 2": "3730"}),
                         {"Lambton": "4198", "Iceland 4": "4217", "Westwood 2": "3730"})


class Match(unittest.TestCase):
    def test_one_pad_building(self):
        self.assertEqual(livebarn.surface_for("Lambton Arena", "4100 Dundas St W York, ON", KNOWN), "4198")

    def test_pad_named_in_the_venue(self):
        self.assertEqual(livebarn.surface_for("Scotiabank Pond - Rink 3", None, KNOWN), "4089")
        self.assertEqual(livebarn.surface_for("Iceland 4", None, KNOWN), "4217")

    def test_no_pad_in_a_many_pad_building_is_no_link(self):
        self.assertIsNone(livebarn.surface_for("Scotiabank Pond", None, KNOWN))

    def test_pad_we_have_not_learned_is_no_link(self):
        self.assertIsNone(livebarn.surface_for("Scotiabank Pond - Rink 1", None, KNOWN))

    def test_unknown_building_is_no_link(self):
        self.assertIsNone(livebarn.surface_for("Sample Arena - Big rink", "123 Sample Rd", KNOWN))

    def test_links_skip_the_redirects(self):
        live, replay = livebarn.links("https://livebarn.com/en/video/4198/2026-10-18/13:10")
        self.assertEqual(live, "https://watch.livebarn.com/en/video/4198/live")
        self.assertEqual(replay, "https://watch.livebarn.com/en/video/4198/2026-10-18/13:10")
        self.assertIsNone(livebarn.links("https://example.com/en/video/4198/2026-10-18/13:10"))
        self.assertIsNone(livebarn.links(""))

    def test_link(self):
        self.assertEqual(livebarn.url("4198", datetime(2026, 10, 15, 19, 0)),
                         "https://livebarn.com/en/video/4198/2026-10-15/19:00")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Unit tests for rink directions. No network.

The behaviour worth protecting is that every rink resolves to the right
building, and that a rink we cannot place gets no link rather than a guess.
"""

import json
import unittest

import arenas


class FindArena(unittest.TestCase):
    def check(self, rink, building):
        found = arenas.find(rink)
        self.assertIsNotNone(found, rink)
        self.assertEqual(found["name"], building)

    def test_pad_numbers_letters_and_sides_are_dropped(self):
        self.check("Iceland 4", "Iceland")
        self.check("Vaughan Sports Village B", "The (Vaughan) Sports Village")
        self.check("Al Palladini West", "Al Palladini Community Centre")
        self.check("Etobicoke Centennial East", "Etobicoke Centennial Arena")

    def test_generic_words_do_not_block_a_match(self):
        self.check("Lambton", "Lambton Arena")
        self.check("Erin Mills 1", "Erin Mills Twin Arenas")
        self.check("Vic Johnston", "Vic Johnston Community Centre")

    def test_renamed_buildings(self):
        self.check("Mississauga Sports and Entertainment Centre 2",
                   "Paramount Fine Foods Centre (Formerly Hersey Centre)")
        self.check("CWENCH Centre Etobicoke 1", "Etobicoke Canlan Ice Sports")
        self.check("NFP Athletic Centre - Canlan York 5", "York Canlan Ice Sports")
        self.check("Pinepoint", "Pine Point Arena")

    def test_unknown_or_ambiguous_rinks_get_no_link(self):
        self.assertIsNone(arenas.find("Somewhere Else 2"))
        # Etobicoke and Scarborough both have a Centennial arena.
        self.assertIsNone(arenas.find("Centennial 1"))
        self.assertIsNone(arenas.directions_url(""))

    def test_link_points_at_the_gthl_address(self):
        url = arenas.directions_url("Lambton")
        self.assertTrue(url.startswith("https://www.google.com/maps/dir/?api=1&destination="))
        self.assertIn("4100%20Dundas%20Street%20West", url)

    def test_apple_maps_link_carries_the_same_address(self):
        url = arenas.apple_directions_url("Iceland 4")
        self.assertTrue(url.startswith("https://maps.apple.com/?daddr="))
        self.assertIn("705%20Matheson%20Boulevard%20East", url)
        self.assertIsNone(arenas.apple_directions_url("Somewhere Else 2"))

    def test_every_rink_seen_this_season_resolves(self):
        with open("season_schedule.json", encoding="utf-8") as f:
            data = json.load(f)
        games = data.get("games", data)
        games = games.values() if isinstance(games, dict) else games
        missing = sorted({g["arena"] for g in games if g.get("arena") and not arenas.find(g["arena"])})
        self.assertEqual(missing, [], "add these to arenas.RENAMED, with a source")


if __name__ == "__main__":
    unittest.main()

"""A team-calendar opponent gets the logo of the club it names, and never another club's."""
import os
import tempfile
import unittest

import page_common


class LogoFile(unittest.TestCase):
    def folder(self, *names):
        d = tempfile.mkdtemp()
        for n in names:
            open(os.path.join(d, n), "wb").close()
        return d

    def test_an_exact_name_wins(self):
        d = self.folder("toronto-eagles.png", "toronto-eagles-aa.png")
        self.assertEqual(page_common.logo_file("Toronto Eagles", d), "toronto-eagles.png")

    def test_a_short_calendar_name_finds_its_club(self):
        d = self.folder("glancaster-bombers.png", "stoney-creek-warriors.png", "mississauga-rattlers.png")
        self.assertEqual(page_common.logo_file("Glancaster", d), "glancaster-bombers.png")
        self.assertEqual(page_common.logo_file("Stoney Creek", d), "stoney-creek-warriors.png")
        self.assertEqual(page_common.logo_file("Rattlers", d), "mississauga-rattlers.png")

    def test_two_clubs_that_fit_give_no_logo(self):
        d = self.folder("mississauga-beast.png", "mississauga-jets.png")
        self.assertIsNone(page_common.logo_file("Mississauga", d))

    def test_an_unknown_club_and_an_empty_name_give_none(self):
        d = self.folder("glancaster-bombers.png")
        self.assertIsNone(page_common.logo_file("Somewhere Else", d))
        self.assertIsNone(page_common.logo_file("", d))

    def test_the_real_cache_has_the_tournament_clubs(self):
        for name in ("Glancaster", "Stoney Creek", "Rattlers", "North Stars"):
            self.assertIsNotNone(page_common.logo_file(name), name)
        self.assertIn('assets/logos/', page_common.team_logo("Glancaster"))
        self.assertIn("team-mono", page_common.team_logo("Rattlers or North Stars"))


if __name__ == "__main__":
    unittest.main()

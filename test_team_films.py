"""
Every game of ours that has a film shows it, tournament and exhibition games from the team calendar as well as the league's.
A film is kept under its date and teams; the calendar only knows a date and an opponent, so this checks the pairing and the icon.
"""
import unittest

import generate_event_pages as ep
import generate_schedule_html as gs

TZ = "2026-11-%02dT%s:00-05:00"


def game(uid, day, hour, opponent, home=False):
    return {"uid": uid, "kind": "game", "start": TZ % (day, hour), "opponent": opponent, "home": home, "timed": True,
            "venue": "Iceland Arena - Rink 2", "label": "Tournament"}


VIDEOS = {
    "2026-11-07_toronto-eagles_at_glancaster-bombers": "https://youtu.be/AAA",
    "2026-11-07_mississauga-rattlers_at_toronto-eagles": "https://youtu.be/BBB",
    "2026-11-08_stoney-creek-warriors_at_toronto-eagles": "https://youtu.be/CCC",
    "2026-11-08_mississauga-north-stars_at_toronto-eagles": "https://youtu.be/DDD",
    "2026-11-09_toronto-eagles_at_somewhere-else": "https://youtu.be/EEE",
    "2026-11-07_mississauga-beast_at_vaughan-rangers": "https://youtu.be/NOPE",
}


class TeamFilms(unittest.TestCase):
    def test_a_game_takes_the_film_of_its_day_and_opponent(self):
        events = [game("a", 7, "14:00", "Glancaster"), game("b", 7, "09:00", "Rattlers", True)]
        self.assertEqual(gs.team_films(events, VIDEOS), {"a": "https://youtu.be/AAA", "b": "https://youtu.be/BBB"})

    def test_an_opponent_the_calendar_is_unsure_of_still_gets_the_only_film_left(self):
        events = [game("s", 8, "08:00", "Stoney Creek"), game("f", 8, "12:45", "Rattlers or North Stars", True)]
        self.assertEqual(gs.team_films(events, VIDEOS), {"s": "https://youtu.be/CCC", "f": "https://youtu.be/DDD"})

    def test_an_unsure_opponent_names_its_own_film_not_the_other_games(self):
        events = [game("f", 8, "12:45", "Rattlers or North Stars", True), game("s", 8, "08:00", "Stoney Creek")]
        self.assertEqual(gs.team_films(events, VIDEOS)["f"], "https://youtu.be/DDD")

    def test_a_game_with_no_film_gets_none_and_other_clubs_films_are_ignored(self):
        events = [game("x", 6, "09:00", "Anyone")]
        self.assertEqual(gs.team_films(events, VIDEOS), {})
        self.assertNotIn("https://youtu.be/NOPE", gs.team_films([game("y", 7, "10:00", "Beast"), game("z", 7, "11:00", "Vaughan")], VIDEOS).values())

    def test_one_film_is_never_given_to_two_games(self):
        events = [game("a", 7, "14:00", "Glancaster"), game("b", 7, "16:00", "Glancaster")]
        self.assertEqual(list(gs.team_films(events, VIDEOS).values()).count("https://youtu.be/AAA"), 1)


class Rows(unittest.TestCase):
    def test_the_row_shows_a_film_icon_that_opens_the_video(self):
        e = game("a", 7, "14:00", "Glancaster")
        html = gs.team_game_row(e, gs.datetime.fromisoformat(e["start"]), film="https://youtu.be/AAA")
        self.assertIn('class="icon-btn game-video"', html)
        self.assertIn('href="https://youtu.be/AAA"', html)
        self.assertIn('data-tip="Watch on YouTube"', html)

    def test_no_film_no_icon(self):
        e = game("a", 7, "14:00", "Glancaster")
        self.assertNotIn("game-video", gs.team_game_row(e, gs.datetime.fromisoformat(e["start"])))

    def test_the_game_page_has_the_film_button(self):
        e = game("a", 7, "14:00", "Glancaster")
        self.assertIn("Watch on YouTube", ep.watch(e, gs.datetime.fromisoformat(e["start"]), "https://youtu.be/AAA"))

    def test_the_build_puts_the_icon_in_the_team_schedule_only_when_it_has_the_film(self):
        e = game("a", 7, "14:00", "Glancaster")
        e["uid"] = "uid-a"
        html = gs.build_block([], gs.datetime(2026, 11, 8).date(), "toronto eagles", [e], videos=VIDEOS)
        self.assertIn("https://youtu.be/AAA", html)
        self.assertNotIn("https://youtu.be/AAA", gs.build_block([], gs.datetime(2026, 11, 8).date(), "toronto eagles", [e]))


class WholeIce(unittest.TestCase):
    PANOS = {"2026-11-07_toronto-eagles_at_glancaster-bombers": "https://youtu.be/PANO"}

    def test_a_game_with_a_whole_ice_video_gets_a_menu_with_both_choices(self):
        e = game("a", 7, "14:00", "Glancaster")
        html = gs.team_video_link("https://youtu.be/AAA", e, "https://youtu.be/PANO")
        self.assertIn("film-pick-btn", html)
        self.assertRegex(html, r'href="https://youtu.be/AAA"[^>]*>Follows play</a>')
        self.assertRegex(html, r'href="https://youtu.be/PANO"[^>]*>Whole ice</a>')

    def test_a_game_without_one_keeps_the_plain_icon(self):
        e = game("a", 7, "14:00", "Glancaster")
        self.assertNotIn("film-pick", gs.team_video_link("https://youtu.be/AAA", e))

    def test_the_panos_follow_the_same_pairing_as_the_films(self):
        events = [game("a", 7, "14:00", "Glancaster"), game("b", 7, "09:00", "Rattlers", True)]
        self.assertEqual(gs.team_panos(events, VIDEOS, self.PANOS), {"a": "https://youtu.be/PANO"})

    def test_the_game_page_offers_both(self):
        e = game("a", 7, "14:00", "Glancaster")
        html = ep.watch(e, gs.datetime.fromisoformat(e["start"]), "https://youtu.be/AAA", "https://youtu.be/PANO")
        self.assertEqual(html.count("film-pick-btn"), 1, "one button, with the choices in its menu")
        self.assertIn("film-pick-btn", html)
        self.assertRegex(html, r'href="https://youtu.be/AAA"[^>]*>Follows play</a>')
        self.assertRegex(html, r'href="https://youtu.be/PANO"[^>]*>Whole ice</a>')

    def test_the_menu_script_and_style_are_on_the_page(self):
        import page_common
        self.assertIn("film-pick-btn", page_common.SCHEDULE_JS)
        self.assertIn(".film-pick.is-open .film-menu", page_common.PAGE_CSS)
        # enhance() runs again after the team login; two listeners would open and close the menu in one tap (node check_film_menu.mjs)
        self.assertIn("data-film-menus", page_common.SCHEDULE_JS)


if __name__ == "__main__":
    unittest.main()

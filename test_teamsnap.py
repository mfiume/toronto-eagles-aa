#!/usr/bin/env python3
"""
Unit tests for the team calendar and its encryption. No network.

The calendar here is made up, in TeamSnap's format. The behaviour worth
protecting is that free-text notes never survive parsing, that our league games
pick up their TeamSnap details without being listed twice, and that nothing
from the team calendar reaches the published page unencrypted.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime

import generate_schedule_html as gen
import team_crypto
import teamsnap

SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:p1
DTSTART;TZID=America/Toronto:20261017T183000
DTEND;TZID=America/Toronto:20261017T200000
SUMMARY:Toronto Eagles U11 AA - Regular practice
LOCATION:123 Sample Rd Toronto\\, ON\\, Canada
DESCRIPTION:Location: Sample Arena - Big rink\\nPlease indicate your presenc
 e on TeamSnap  (Arrival Time:  6:00 PM (America/Toronto))\\nCall Coach Pa
 t at 416-555-0100 if late
END:VEVENT
BEGIN:VEVENT
UID:d1
DTSTART;TZID=America/Toronto:20261024T100000
DTEND;TZID=America/Toronto:20261024T110000
SUMMARY:Toronto Eagles U11 AA - Eagles - dryland
LOCATION:400 Sample Ave Etobicoke\\, ON\\, Canada
DESCRIPTION:Location: Sample Centre - Gym\\nGym clothes  (Arrival Time:  9:
 45 AM (America/Toronto))
END:VEVENT
BEGIN:VEVENT
UID:g1
DTSTART;TZID=America/Toronto:20261018T131000
DTEND;TZID=America/Toronto:20261018T141000
SUMMARY:Toronto Eagles U11 AA regular season game vs Westmall Lightning
LOCATION:4100 Dundas St W York\\, ON\\, Canada
DESCRIPTION:Location: Lambton Arena\\nUniform: white (Arrival Time: 12:20 PM
  (America/Toronto))
END:VEVENT
BEGIN:VEVENT
UID:x1
DTSTART;TZID=America/Toronto:20261015T190000
DTEND;TZID=America/Toronto:20261015T200000
SUMMARY:Toronto Eagles U11 AA exhibition game vs Sample Visitors
LOCATION:4100 Dundas St W York\\, ON\\, Canada
DESCRIPTION:Location: Lambton Arena\\nUniform: White (Arrival Time:  6:10 PM
  (America/Toronto))
END:VEVENT
BEGIN:VEVENT
UID:t1
DTSTART;TZID=America/Toronto:20261107T080000
DTEND;TZID=America/Toronto:20261107T080000
SUMMARY:Toronto Eagles U11 AA - Sample Tournament
LOCATION:TBC
DESCRIPTION:
END:VEVENT
END:VCALENDAR
"""

LEAGUE_GAME = {"Date": "18-Oct-2026 Sun", "Time": "1:10 PM", "Away": "West Mall Lightning",
               "Score": ":", "Home": "Toronto Eagles", "Arena": "Lambton"}


class ParseCalendar(unittest.TestCase):
    def setUp(self):
        self.events = {e["uid"]: e for e in teamsnap.events_from_ics(SAMPLE_ICS)}

    def test_kinds(self):
        kinds = {uid: e["kind"] for uid, e in self.events.items()}
        self.assertEqual(kinds, {"p1": "practice", "d1": "dryland", "g1": "game",
                                 "x1": "game", "t1": "tournament"})

    def test_folded_lines_and_details(self):
        p = self.events["p1"]
        self.assertEqual(p["venue"], "Sample Arena - Big rink")
        self.assertEqual(p["arrive"], "6:00 PM")
        self.assertEqual(p["address"], "123 Sample Rd Toronto, ON, Canada")
        self.assertEqual(self.events["d1"]["wear"], "Gym clothes")
        self.assertEqual(self.events["d1"]["arrive"], "9:45 AM")

    def test_free_text_notes_are_dropped(self):
        everything = json.dumps(list(self.events.values()))
        self.assertNotIn("555-0100", everything)
        self.assertNotIn("Coach", everything)
        self.assertNotIn("presence", everything)

    def test_games(self):
        x = self.events["x1"]
        self.assertEqual((x["opponent"], x["home"], x["label"]), ("Sample Visitors", True, "Exhibition"))
        self.assertEqual(self.events["g1"]["wear"], "white")

    def test_placeholder_times_and_tbc_locations(self):
        t = self.events["t1"]
        self.assertFalse(t["timed"])
        self.assertIsNone(t["address"])


class MatchLeagueGames(unittest.TestCase):
    def test_league_game_takes_teamsnap_details_once(self):
        events = teamsnap.events_from_ics(SAMPLE_ICS)
        # On the 16th the league game is the next one, so its card carries
        # TeamSnap's arrival time and jersey; its row does not.
        html = gen.build_block([LEAGUE_GAME], date(2026, 10, 16), "toronto eagles", events)
        self.assertEqual(html.count("Arrive 12:20 PM · White jersey"), 1)
        # The TeamSnap copy of the league game is not listed again.
        self.assertNotIn("Westmall", html)
        # The exhibition game is ours only in TeamSnap, so it is listed.
        self.assertIn("Sample Visitors", html)
        self.assertIn("Exhibition", html)


class TeamScores(unittest.TestCase):
    def test_exhibition_with_a_score_reads_like_a_final(self):
        events = teamsnap.events_from_ics(SAMPLE_ICS)
        x = next(e for e in events if e["uid"] == "x1")
        gen._TEAM_SCORES = {gen.score_key(x): "3-1"}
        try:
            row = gen.team_game_row(x, datetime.fromisoformat(x["start"]))
        finally:
            gen._TEAM_SCORES = None
        self.assertIn("Final", row)
        self.assertIn('result-w', row)
        self.assertIn('<span class="game-goals r2 won">3</span>', row)   # We were home.
        self.assertIn('<span class="game-goals r1 lost">1</span>', row)

    def test_score_key_hides_the_opponent(self):
        key = gen.score_key({"start": "2026-10-15T19:00", "opponent": "Burlington Eagles"})
        self.assertEqual(key, "2ed1dce2be0e")


class PublishedPage(unittest.TestCase):
    def test_round_trip_and_wrong_password(self):
        sealed = team_crypto.encrypt("hello", "four random words here")
        self.assertEqual(team_crypto.decrypt(sealed, "four random words here"), "hello")
        with self.assertRaises(Exception):
            team_crypto.decrypt(sealed, "wrong")

    def test_nothing_from_the_calendar_is_published_in_the_clear(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with tempfile.TemporaryDirectory() as tmp:
            for name in os.listdir(here):
                if name.endswith(".py") or name == "arenas.json":
                    shutil.copy(os.path.join(here, name), tmp)
            shutil.copytree(os.path.join(here, "assets"), os.path.join(tmp, "assets"))
            # A league game before every sample event, so the page's window
            # covers them whatever today's date is.
            early = dict(LEAGUE_GAME, Date="01-Oct-2026 Thu")
            with open(os.path.join(tmp, "schedule.json"), "w") as f:
                json.dump({"schedule": [early], "timestamp": "2026-10-13T12:00:00+00:00"}, f)
            with open(os.path.join(tmp, "calendar.ics"), "w") as f:
                f.write(SAMPLE_ICS)
            env = dict(os.environ, TEAM_EVENTS_PASSWORD="four random words here")
            subprocess.run([sys.executable, "teamsnap.py", "calendar.ics"], cwd=tmp, check=True,
                           capture_output=True)
            subprocess.run([sys.executable, "generate_schedule_html.py"], cwd=tmp, env=env,
                           check=True, capture_output=True)
            subprocess.run([sys.executable, "generate_event_pages.py"], cwd=tmp, env=env,
                           check=True, capture_output=True)
            page = open(os.path.join(tmp, "schedule.html"), encoding="utf-8").read()
            event_pages = [open(os.path.join(tmp, n), encoding="utf-8").read()
                           for n in sorted(os.listdir(tmp)) if n.startswith("event-")]
        # One per team event. (The league game here is moved to Oct 1, so its
        # TeamSnap entry is not matched to it and gets a page of its own.)
        self.assertEqual(len(event_pages), 5)
        for published in [page] + event_pages:
            for secret in ("Sample Arena", "Sample Centre", "Sample Visitors", "Arrive",
                           "123 Sample Rd", "Sample Tournament", "Gym clothes", "Practice",
                           "Dryland"):
                self.assertNotIn(secret, published.replace("Practices, dryland", ""))
        opened = ""
        for published in event_pages:
            sealed = json.loads(re.search(r'id="team-events">(.*?)</script>', published, re.S)
                                .group(1).replace("<\\/", "</"))
            opened += team_crypto.decrypt(sealed, "four random words here")
        for detail in ("Sample Visitors", "Sample Tournament", "Gym clothes", "6:00 PM"):
            self.assertIn(detail, opened)
        payload = json.loads(re.search(r'id="team-events">(.*?)</script>', page, re.S)
                             .group(1).replace("<\\/", "</"))
        self.assertIn("Sample Visitors", team_crypto.decrypt(payload, "four random words here"))


if __name__ == "__main__":
    unittest.main()

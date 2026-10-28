#!/usr/bin/env python3
"""The game sheets at rest: sealed in the repository, opened only with the team password, migrated from the old plain file."""

import json
import os
import tempfile
import unittest
from unittest import mock

import sheet_store

SHEETS = {"2026-10-01_a_at_b": {"home": "Toronto Eagles", "away": "Rivals", "final": {"home": 3, "away": 1}, "goals": [], "penalties": []}}


class SheetStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.old = os.getcwd()
        os.chdir(self.dir.name)
        self.env = mock.patch.dict(os.environ, {"TEAM_EVENTS_PASSWORD": "team pass"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        os.chdir(self.old)
        self.dir.cleanup()

    def test_saved_sheets_are_sealed_and_open_with_the_password(self):
        self.assertTrue(sheet_store.save(SHEETS))
        raw = open(sheet_store.SEALED_FILE).read()
        for visible in ("Toronto Eagles", "Rivals", "goals", "final"):
            self.assertNotIn(visible, raw)
        self.assertEqual(sheet_store.load(), SHEETS)

    def test_a_wrong_password_gives_nothing_rather_than_an_error(self):
        sheet_store.save(SHEETS)
        with mock.patch.dict(os.environ, {"TEAM_EVENTS_PASSWORD": "another"}):
            self.assertEqual(sheet_store.load(), {})

    def test_without_a_password_nothing_is_read_or_written(self):
        sheet_store.save(SHEETS)
        with mock.patch.dict(os.environ, {"TEAM_EVENTS_PASSWORD": ""}):
            self.assertEqual(sheet_store.load(), {})
            self.assertFalse(sheet_store.save({"x": 1}))
        self.assertEqual(sheet_store.load(), SHEETS)

    def test_the_old_plain_file_is_sealed_once_and_removed(self):
        with open(sheet_store.LEGACY_FILE, "w") as f:
            json.dump(SHEETS, f)
        self.assertTrue(sheet_store.migrating())
        self.assertEqual(sheet_store.load(), SHEETS)
        sheet_store.save(sheet_store.load())
        self.assertFalse(os.path.exists(sheet_store.LEGACY_FILE))
        self.assertFalse(sheet_store.migrating())
        self.assertEqual(sheet_store.load(), SHEETS)

    def test_the_old_plain_file_is_left_alone_without_a_password(self):
        with open(sheet_store.LEGACY_FILE, "w") as f:
            json.dump(SHEETS, f)
        with mock.patch.dict(os.environ, {"TEAM_EVENTS_PASSWORD": ""}):
            self.assertFalse(sheet_store.migrating())
            self.assertFalse(sheet_store.save(SHEETS))
        self.assertTrue(os.path.exists(sheet_store.LEGACY_FILE))

    def test_no_file_is_no_sheets(self):
        self.assertEqual(sheet_store.load(), {})


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Unit tests for reading the GTHL schedule table. No network, no browser.

The rows are stand-ins for Selenium elements, shaped like the markup the GTHL
served on 2026-10-11: away, score and home merged into one cell spanning three
columns, every other cell carrying a data-label.
"""

import unittest

import scrape_schedule as sc

HEADERS = ["Date", "Time", "Away", "Score", "Home", "Arena", "Region", "Div/Cat", "Type", ""]


class El:
    """Just enough of a Selenium WebElement for parse_rows."""

    def __init__(self, tag, text="", attrs=None, children=()):
        self.tag, self._text, self.attrs, self.children = tag, text, attrs or {}, list(children)

    @property
    def text(self):
        own = [self._text] if self._text else []
        return "\n".join(own + [c.text for c in self.children if c.text])

    def get_attribute(self, name):
        return self.attrs.get(name)

    def _all(self):
        for child in self.children:
            yield child
            yield from child._all()

    def _matches(self, selector):
        selector = selector.strip()
        if "." in selector:
            tag, cls = selector.split(".", 1)
            return (not tag or tag == self.tag) and cls in (self.attrs.get("class") or "").split()
        return self.tag == selector

    def find_elements(self, by, selector):
        return [e for e in self._all() if any(e._matches(s) for s in selector.split(","))]


def td(text, label=None, **attrs):
    if label:
        attrs["data-label"] = label
    return El("td", text, attrs)


def match_cell(away, score, home, logos=("A.png", "H.png")):
    return El("td", attrs={"class": "match-container align-middle", "colspan": "3"}, children=[
        El("span", attrs={"class": "cell-match g-0"}, children=[
            El("span", attrs={"class": "logo-span item item-1"},
               children=[El("img", attrs={"class": "logo-img mx-auto d-block", "src": logos[0]})]),
            El("span", away, {"class": "cell-away item item-2"}),
            El("span", score, {"class": "cell-score item item-3"}),
            El("span", home, {"class": "cell-home item item-4"}),
            El("span", attrs={"class": "logo-span item item-5"},
               children=[El("img", attrs={"class": "logo-img mx-auto d-block", "src": logos[1]})]),
        ])])


def table(*rows):
    header = El("tr", children=[El("th", h) for h in HEADERS])
    return El("table", children=[header, *rows])


def merged_row(away="Vaughan Panthers", score=":", home="Humber Valley Sharks"):
    return El("tr", children=[
        td("12-Oct-2026 Mon", "Date"), td("7:10 PM", "Time"),
        match_cell(away, score, home),
        td("Scotiabank Pond 2", "Arena"), td("West", "Region"),
        td("Under 11 / AA", "Div/Cat"), td("LG", "Type"), td(""),
    ])


class ParseRows(unittest.TestCase):
    def test_merged_match_cell(self):
        [game] = sc.parse_rows(table(merged_row()), HEADERS)
        self.assertEqual(game["Away"], "Vaughan Panthers")
        self.assertEqual(game["Home"], "Humber Valley Sharks")
        self.assertEqual(game["Score"], ":")
        self.assertEqual(game["AwayLogo"], "A.png")
        self.assertEqual(game["HomeLogo"], "H.png")

    def test_columns_after_the_merged_cell_do_not_shift(self):
        [game] = sc.parse_rows(table(merged_row()), HEADERS)
        self.assertEqual(game["Arena"], "Scotiabank Pond 2")
        self.assertEqual(game["Div/Cat"], "Under 11 / AA")
        self.assertEqual(game["Type"], "LG")
        self.assertEqual(sc.wrong_division([game]), [])

    def test_played_score_loses_its_spaces(self):
        [game] = sc.parse_rows(table(merged_row(score="3 : 2")), HEADERS)
        self.assertEqual(game["Score"], "3:2")

    def test_old_layout_without_labels_still_reads_by_position(self):
        row = El("tr", children=[td(v) for v in (
            "12-Oct-2026 Mon", "7:10 PM", "Vaughan Panthers", ":", "Humber Valley Sharks",
            "Scotiabank Pond 2", "West", "Under 11 / AA", "LG")])
        [game] = sc.parse_rows(table(row), HEADERS)
        self.assertEqual(game["Home"], "Humber Valley Sharks")
        self.assertEqual(game["Div/Cat"], "Under 11 / AA")

    def test_blank_template_row_is_skipped(self):
        row = El("tr", children=[td("") for _ in range(9)])
        self.assertEqual(sc.parse_rows(table(row), HEADERS), [])


if __name__ == "__main__":
    unittest.main()

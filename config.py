#!/usr/bin/env python3
"""
Single source of truth for which team, division and season this hub tracks.

Everything else (both scrapers, all three page generators, the docs) reads from
here, so moving up an age group next year is a change to this file only.

GTHL/AGILEX dropdown values, for reference:
  Division (ddlDiv)   U10 .. U21          -> displayed as "Under 10" .. "Under 21"
  Category (ddlCat)   A3 = AAA, A2 = AA, A1 = A
  Region   (ddlRegion) East / West        -> standings only; absent until the
                                             division has posted standings
  Season   (ddlSeason) "26-27", "25-26", ...
"""

# --- Team -------------------------------------------------------------------
TEAM_NAME = "Toronto Eagles"

# --- Division ---------------------------------------------------------------
SEASON = "26-27"
DIVISION = "U11"            # ddlDiv value
DIVISION_LABEL = "Under 11"  # how the site spells it in the Div/Cat column
CATEGORY = "AA"              # human label
CATEGORY_VALUE = "A2"        # ddlCat value for AA
REGION = "West"              # ddlRegion value

# Headline used across the three pages.
SITE_TITLE = f"{TEAM_NAME} {DIVISION} {CATEGORY}"

# --- Schedule window --------------------------------------------------------
# Games from DAYS_BACK ago through DAYS_AHEAD from now. Looking back a week
# keeps the previous weekend's results on the page instead of dropping a game
# the morning after it is played.
SCHEDULE_DAYS_BACK = 7
SCHEDULE_DAYS_AHEAD = 90

# --- Playoff format --------------------------------------------------------
# The GTHL publishes the playoff structure per division per season, and it is
# not derivable from the standings. Fill this in once the format for the season
# above is published; until then the playoffs page says so rather than assuming
# last season's structure still holds.
#
# Shape, using 25-26 U10 AA West as the worked example:
#
#   PLAYOFF_FORMAT = {
#       "direct_cutoff": 6,           # positions 1..6 go straight to Round 1
#       "pools": {"A": [7, 10, 11, 14],
#                 "B": [8, 9, 12, 13]},
#       "notes": [
#           "<strong>First Round:</strong> ...",
#           "<strong>Preliminary Round:</strong> ...",
#       ],
#   }
PLAYOFF_FORMAT = None

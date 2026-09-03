#!/usr/bin/env python3
"""
Check the scrapers against the live GTHL site before deploying.

Run this after changing config.py or after the GTHL changes its stats app:

    python test_scraper.py

It verifies the two things that can silently go wrong. The season filter can
fail to apply, in which case the site serves the previous season's table under
this season's heading; and the division filter can fail to apply, in which case
the schedule fills up with another age group's games. Both are caught by
reading back the labels the site itself prints.
"""

import sys

import config


def check_caption_guard():
    """The season/division guard must reject a caption for the wrong season."""
    from scrape_standings import caption_matches

    good = f"{config.SEASON} SEASON -- {config.DIVISION} {config.CATEGORY_VALUE} {config.REGION}"
    cases = [
        (good, True, "the configured season, division and category"),
        (good.replace(config.SEASON, "24-25"), False, "a different season"),
        (good.replace(config.DIVISION, "U13"), False, "a different division"),
        (good.replace(config.CATEGORY_VALUE, "A3"), False, "a different category"),
        ("", False, "a missing caption"),
    ]

    ok = True
    for caption, expected, description in cases:
        if caption_matches(caption) != expected:
            print(f"  FAIL: guard {'rejected' if expected else 'accepted'} {description}")
            ok = False
    print("  Season/division guard: " + ("ok" if ok else "BROKEN"))
    return ok


def check_standings():
    """Scrape standings and report what the site actually served."""
    from scrape_standings import scrape_standings

    data = scrape_standings()
    if "error" in data:
        print(f"  FAIL: {data['error']}")
        return False

    filters = data["filters"]
    standings = data["standings"]
    print(f"  Site reported: {filters['source_label']!r}")
    print(f"  Region filter applied: {filters['region_applied']}")
    print(f"  Teams: {len(standings)}")

    if not standings:
        print(f"  No standings posted yet for {config.SEASON} "
              f"{config.DIVISION} {config.CATEGORY}. Expected before the season starts.")
        return True

    if not filters["region_applied"]:
        print("  Note: showing the whole division, not just "
              f"{config.REGION}, because the site offered no region filter.")

    for team in standings:
        marker = " <-- us" if team["Team"] == config.TEAM_NAME else ""
        print(f"    {team['Position']:>2} {team['Team']:<28} "
              f"{team['W-L-T']:>8} {team['PTS']:>3} pts{marker}")

    if not any(t["Team"] == config.TEAM_NAME for t in standings):
        print(f"  WARNING: {config.TEAM_NAME} is not in this table. Check "
              "DIVISION, CATEGORY and REGION in config.py.")
    return True


def check_schedule():
    """Scrape the schedule and report our own games."""
    from scrape_schedule import scrape_schedule

    data = scrape_schedule()
    if "error" in data:
        print(f"  FAIL: {data['error']}")
        return False

    games = data["schedule"]
    filters = data["filters"]
    print(f"  Window: {filters['from_date']} to {filters['to_date']}")
    print(f"  Games in the division: {len(games)}")

    ours = [g for g in games
            if config.TEAM_NAME in (g.get("Away", ""), g.get("Home", ""))]
    print(f"  {config.TEAM_NAME} games: {len(ours)}")
    for game in ours:
        print(f"    {game['Date']} {game['Time']:>8}  "
              f"{game['Away']} at {game['Home']} ({game['Arena']})")
    return True


def main():
    print("=" * 64)
    print(f"Testing scrapers for {config.SITE_TITLE}, season {config.SEASON}")
    print("=" * 64)

    results = []
    for name, check in [
        ("Guard logic", check_caption_guard),
        ("Standings", check_standings),
        ("Schedule", check_schedule),
    ]:
        print(f"\n{name}:")
        try:
            results.append(check())
        except Exception as e:
            print(f"  FAIL: unexpected error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 64)
    if all(results):
        print("All checks passed.")
        return 0
    print("Some checks failed. Do not deploy until they pass.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

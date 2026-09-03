# Toronto Eagles U11 AA - Team Hub

Automated team hub for the Toronto Eagles U11 AA hockey team, tracking standings
and schedule from the GTHL (Greater Toronto Hockey League).

**Live page: https://mfiume.github.io/toronto-eagles-aa/**

## Features

- Standings for the division, with the Eagles highlighted and club logos
- Schedule with scores, Eagles games highlighted
- Playoff seeding picture, once the GTHL publishes the format for the season
- Rebuilt hourly by GitHub Actions, published by GitHub Pages, no server to run

## Configuration

Everything about which team, division and season is tracked lives in one place,
`config.py`:

```python
TEAM_NAME = "Toronto Eagles"
SEASON = "26-27"
DIVISION = "U11"             # ddlDiv value
DIVISION_LABEL = "Under 11"  # how the site spells it in the Div/Cat column
CATEGORY = "AA"              # human label
CATEGORY_VALUE = "A2"        # ddlCat value for AA
REGION = "West"              # ddlRegion value
```

Moving up an age group each season is a change to this file only. Both scrapers,
all three page generators and the test script read from it.

GTHL dropdown values, for reference:

| Dropdown | Values |
| --- | --- |
| Season (`ddlSeason`) | `26-27`, `25-26`, `24-25`, ... |
| Division (`ddlDiv`) | `U10` .. `U21`, displayed as "Under 10" .. "Under 21" |
| Category (`ddlCat`) | `A3` = AAA, `A2` = AA, `A1` = A |
| Region (`ddlRegion`) | `East`, `West` (standings only) |

## Two traps in the GTHL stats app

The site embeds the AGILEX stats app in an iframe and drives it with ASP.NET
postbacks. Two behaviours will hand you the wrong data without any error:

**The season dropdown lies on page load.** It displays the newest season, but the
server renders the newest season that actually has standings posted. In early
September 2026 the dropdown read "26-27" while the table below it was the final
25-26 table. Selecting the option the page already shows fires no change event
and therefore no postback, so the season filter silently does nothing.
`scrape_standings.select_season()` forces the postback by selecting another
season first and then the one we want.

**The region dropdown is not always there.** It only exists once a division has
standings groups, so it is absent for a season that has not started. That is not
an error. The scrape records `region_applied` and the pages say whether they are
showing one region or the whole division.

Both scrapers defend against this by reading back the labels the site prints for
itself. Standings compares the caption (`#rptMain_st_lbDetail_0`, e.g.
`26-27 SEASON -- U11 A2 West`) against the requested season, division and
category. Schedule compares every row's Div/Cat column against the requested
division. A mismatch is written to the JSON as an error and the run fails, rather
than publishing another season's or another age group's table.

## Testing before you deploy

```bash
pip install -r requirements.txt
python test_scraper.py
```

This exercises the guard logic, then scrapes both sources live and prints what
the site actually served, including which of our games it found. Run it after
changing `config.py` or whenever the GTHL changes its stats app.

To rebuild the pages from data already scraped:

```bash
python generate_html.py
python generate_schedule_html.py
python generate_playoffs_html.py
```

## Playoff format

The GTHL publishes the playoff structure per division per season and it cannot be
derived from the standings, so it is not guessed. `config.PLAYOFF_FORMAT` is
`None` until the format for the current season is known, and the playoffs page
says so. Filling it in seeds the page from the standings:

```python
PLAYOFF_FORMAT = {
    "direct_cutoff": 6,                                    # 1st-6th go straight to Round 1
    "pools": {"A": [7, 10, 11, 14], "B": [8, 9, 12, 13]},  # play-in pools
    "notes": ["<strong>First Round:</strong> ..."],         # shown on the page
}
```

The values above are the 25-26 U10 AA West format, kept as a worked example of
the shape.

## How it works

1. `scrape_standings.py` drives the standings iframe with Selenium, applies the
   filters from `config.py`, verifies what the site served, and writes
   `standings.json`.
2. `scrape_schedule.py` does the same for the schedule iframe over a date window
   (`SCHEDULE_DAYS_BACK` to `SCHEDULE_DAYS_AHEAD` from today) and writes
   `schedule.json`. Both regions are pulled, because interlocking games are
   scheduled across East and West.
3. `generate_html.py`, `generate_schedule_html.py` and
   `generate_playoffs_html.py` turn that JSON into `index.html`,
   `schedule.html` and `playoffs.html`. Shared bits (the "last updated" line,
   header badges, notice styling) live in `page_common.py`.
4. `.github/workflows/scrape-standings.yml` runs the whole chain hourly and on
   demand, then commits and pushes any changes.
5. GitHub Pages publishes the committed HTML.

## Files

```
├── config.py                    # Team, division, season, playoff format
├── page_common.py               # Timestamp, header badges, notice styling
├── scrape_standings.py          # Standings scraper
├── scrape_schedule.py           # Schedule scraper
├── generate_html.py             # Standings page
├── generate_schedule_html.py    # Schedule page
├── generate_playoffs_html.py    # Playoffs page
├── test_scraper.py              # Pre-deploy checks against the live site
├── requirements.txt             # Python dependencies
├── .github/workflows/scrape-standings.yml
├── standings.json               # Scraped data
├── schedule.json                # Scraped data
├── index.html                   # Generated
├── schedule.html                # Generated
└── playoffs.html                # Generated
```

## Troubleshooting

**The run failed with "Refusing to publish standings for the wrong division or
season."** The guard did its job: the site served something other than what
`config.py` asked for. Check that `SEASON`, `DIVISION` and `CATEGORY_VALUE` are
values the site actually offers, then run `python test_scraper.py` to see the
caption it returned.

**Standings are empty.** Expected before the season's first games. The caption in
`standings.json` (`filters.source_label`) confirms which season the site served.

**No table found.** The scraper writes `page_source.html` or
`schedule_page_source.html` when it cannot locate the table. The GTHL may have
changed its markup; update the selectors in `find_standings_table()` or
`find_schedule_table()`.

**GitHub Pages not updating.** Confirm Pages is enabled under Settings → Pages,
deploying from `main` / root. Publishing lags a commit by a few minutes.

**The Action cannot commit.** Settings → Actions → General → Workflow
permissions → "Read and write permissions".

## Credits

Data sourced from [GTHL Canada](https://gthlcanada.com/).

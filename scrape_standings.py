#!/usr/bin/env python3
"""
GTHL Standings Scraper

Scrapes the standings for the division configured in config.py from
gthlcanada.com, which embeds the AGILEX stats app in an iframe.

Two things about that app are worth knowing before changing this file:

1. The season dropdown *displays* the newest season on load, but the server
   renders the newest season that actually has standings posted. In early
   September 2026 the dropdown reads "26-27" while the table below it is the
   final 25-26 table. Selecting the already-selected option fires no change
   event and so no postback, which means the season filter silently does
   nothing. select_season() forces the postback by bouncing off another season
   first.

2. The region dropdown only exists once the division has standings groups, so
   it is absent for a season that has not started. That is not an error; the
   scrape records whether the region filter was applied so the pages can say
   what they are actually showing.

The app prints the filters it really applied into a caption
(#rptMain_st_lbDetail_0), e.g. "26-27 SEASON -- U11 A2 West". We read it back
and refuse to write standings whose season or division does not match what was
asked for, so a repeat of problem 1 fails loudly instead of publishing the
wrong season's table.
"""

import json
import time
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

import config

STANDINGS_URL = "https://gthlcanada.com/standing/"
IFRAME_ID = "iframed-stats"
CAPTION_ID = "rptMain_st_lbDetail_0"

# Seconds to wait after each dropdown change for the ASP.NET postback to land.
POSTBACK_WAIT = 4


def setup_driver():
    """Set up Chrome driver with headless options for GitHub Actions"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    return webdriver.Chrome(options=chrome_options)


def select_option(driver, dropdown_id, value):
    """Select a dropdown value and wait for the postback. True if it was set."""
    try:
        Select(driver.find_element(By.ID, dropdown_id)).select_by_value(value)
    except Exception as e:
        print(f"Could not set {dropdown_id}={value}: {e}")
        return False
    print(f"Selected {dropdown_id}={value}")
    time.sleep(POSTBACK_WAIT)
    return True


def select_season(driver, season):
    """
    Apply the season filter, forcing a postback.

    Selecting the option the page already shows fires no change event, and the
    site would keep rendering the newest season with data. Bouncing off another
    season first guarantees the server sees the season we asked for.
    """
    try:
        dropdown = Select(driver.find_element(By.ID, "ddlSeason"))
        others = [
            o.get_attribute("value")
            for o in dropdown.options
            if o.get_attribute("value") != season
        ]
    except Exception as e:
        print(f"Could not read season dropdown: {e}")
        return False

    if others:
        select_option(driver, "ddlSeason", others[0])
    return select_option(driver, "ddlSeason", season)


def read_caption(driver):
    """The filters the site says it applied, e.g. '26-27 SEASON -- U11 A2 West'."""
    try:
        return driver.find_element(By.ID, CAPTION_ID).text.strip()
    except Exception:
        return ""


def caption_matches(caption):
    """Does the caption confirm the season, division and category we asked for?"""
    if not caption:
        return False
    return (
        config.SEASON in caption
        and config.DIVISION in caption
        and config.CATEGORY_VALUE in caption
    )


def find_standings_table(driver):
    """Locate the standings table, trying the most specific selectors first."""
    for selector in [
        "table.standings",
        "table.wp-block-table",
        "div.standings-table table",
        "div[class*='standing'] table",
        "table",
    ]:
        tables = driver.find_elements(By.CSS_SELECTOR, selector)
        if tables:
            print(f"Found table using selector: {selector}")
            return tables[0]
    return None


def read_headers(table):
    """Column headers, falling back to the layout the site has used."""
    for finder in (
        lambda: table.find_element(By.TAG_NAME, "thead").find_element(By.TAG_NAME, "tr"),
        lambda: table.find_element(By.TAG_NAME, "tr"),
    ):
        try:
            row = finder()
            headers = [th.text.strip() for th in row.find_elements(By.TAG_NAME, "th")]
            if headers:
                return headers
        except Exception:
            continue
    return ["Position", "Team", "GP", "W-L-T", "PTS", "WIN%", "GFA", "GAA",
            "Home", "Away", "P10", "Streak"]


def parse_rows(table, headers):
    """Extract one dict per team, in standings order."""
    standings = []
    position = 1

    for row in table.find_elements(By.TAG_NAME, "tr")[1:]:  # skip header row
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 3:  # spacer row
                continue

            # A division with no standings yet still renders one blank
            # template row, complete with an empty logo. Skip anything with
            # no text in it.
            if not any(cell.text.strip() for cell in cells):
                continue

            row_data = {"Position": position}

            # The team cell carries the club logo.
            try:
                logo_src = cells[0].find_element(By.TAG_NAME, "img").get_attribute("src")
                if logo_src and logo_src.startswith("Images/"):
                    logo_src = f"https://www.agilex.ca/SSP/{logo_src}"
                row_data["Logo"] = logo_src
            except Exception:
                row_data["Logo"] = None

            for i, cell in enumerate(cells):
                if i < len(headers) and headers[i]:
                    row_data[headers[i]] = cell.text.strip()

            standings.append(row_data)
            position += 1
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue

    return standings


def scrape_standings():
    """Scrape the standings for the configured division."""
    driver = setup_driver()

    filters = {
        "division": config.DIVISION,
        "category": config.CATEGORY,
        "region": config.REGION,
        "season": config.SEASON,
        "region_applied": False,
        "source_label": "",
    }

    try:
        print("Navigating to GTHL standings page...")
        driver.get(STANDINGS_URL)
        wait = WebDriverWait(driver, 30)
        time.sleep(5)

        print("Switching to standings iframe...")
        driver.switch_to.frame(
            wait.until(EC.presence_of_element_located((By.ID, IFRAME_ID)))
        )
        time.sleep(5)

        # Division and category first: they survive a season change, and the
        # region dropdown only appears once both are set.
        select_option(driver, "ddlDiv", config.DIVISION)
        select_option(driver, "ddlCat", config.CATEGORY_VALUE)
        select_season(driver, config.SEASON)

        # Region resets on a season change, so it goes last. It is missing
        # entirely for a season with no standings posted yet.
        filters["region_applied"] = select_option(driver, "ddlRegion", config.REGION)
        if not filters["region_applied"]:
            print("No region filter available; the division has no standings groups yet.")

        caption = read_caption(driver)
        filters["source_label"] = caption
        print(f"Site reports: {caption!r}")

        if not caption_matches(caption):
            return {
                "error": (
                    f"GTHL served {caption or 'an unlabelled table'} when asked for "
                    f"{config.SEASON} {config.DIVISION} {config.CATEGORY_VALUE}. "
                    "Refusing to publish standings for the wrong division or season."
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filters": filters,
            }

        table = find_standings_table(driver)
        if not table:
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return {
                "error": "No standings table found",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filters": filters,
            }

        headers = read_headers(table)
        print(f"Headers: {headers}")

        standings = parse_rows(table, headers)
        print(f"Extracted {len(standings)} teams")

        return {
            "standings": standings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filters": filters,
        }

    except Exception as e:
        print(f"Error during scraping: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filters": filters,
        }

    finally:
        driver.quit()


def main():
    print("=" * 60)
    print("GTHL Standings Scraper")
    print(f"Season: {config.SEASON}")
    print(f"Division: {config.DIVISION}, Category: {config.CATEGORY}")
    print(f"Region: {config.REGION}")
    print("=" * 60)

    data = scrape_standings()

    with open("standings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("\nData saved to standings.json")

    if "error" in data:
        print(f"Error: {data['error']}")
        exit(1)

    count = len(data["standings"])
    if count:
        print(f"Successfully scraped {count} teams")
    else:
        # A season that has not started has no standings. Correct, not a failure.
        print(f"No teams posted yet for {config.SEASON} {config.DIVISION} {config.CATEGORY}")
    exit(0)


if __name__ == "__main__":
    main()

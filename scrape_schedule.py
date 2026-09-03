#!/usr/bin/env python3
"""
GTHL Schedule Scraper

Scrapes the schedule for the division configured in config.py from
gthlcanada.com. The schedule app lives in a different iframe from the standings
app and filters by date range rather than by season, so there is no season
dropdown to fight with here: the dates in the results say which season they
belong to.

Both regions are pulled. Interlocking games are scheduled across East and West,
so filtering by region would drop games our team actually plays.
"""

import json
import time
from datetime import datetime, timedelta, timezone

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

import config

SCHEDULE_URL = "https://gthlcanada.com/schedule/"
IFRAME_SELECTOR = "iframe[src*='schedules.aspx']"

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


def set_date(driver, field_id, value):
    """Type a DD-MMM-YYYY date into one of the date fields."""
    try:
        field = driver.find_element(By.ID, field_id)
        field.clear()
        field.send_keys(value)
        print(f"Set {field_id}: {value}")
        time.sleep(1)
        return True
    except Exception as e:
        print(f"Could not set {field_id}: {e}")
        return False


def date_window():
    """The DD-MMM-YYYY range to ask for, from config."""
    now = datetime.now()
    start = now - timedelta(days=config.SCHEDULE_DAYS_BACK)
    end = now + timedelta(days=config.SCHEDULE_DAYS_AHEAD)
    return start.strftime("%d-%b-%Y"), end.strftime("%d-%b-%Y")


def find_schedule_table(driver):
    """Locate the schedule table, trying the most specific selectors first."""
    for selector in [
        "table.schedule",
        "table.wp-block-table",
        "div.schedule-table table",
        "div[class*='schedule'] table",
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
    return ["Date", "Time", "Away", "Score", "Home", "Arena", "Region",
            "Div/Cat", "Type"]


def parse_rows(table, headers):
    """Extract one dict per game, in the order the site lists them."""
    games = []

    for row in table.find_elements(By.TAG_NAME, "tr")[1:]:  # skip header row
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 3:  # spacer row
                continue

            # Blank template rows show up when a date range has no games.
            if not any(cell.text.strip() for cell in cells):
                continue

            game = {}
            for i, cell in enumerate(cells):
                if i < len(headers) and headers[i]:
                    game[headers[i]] = cell.text.strip()

            if game:
                games.append(game)
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue

    return games


def wrong_division(games):
    """
    Games the site returned that are not the division we asked for.

    The Div/Cat column spells out what each game actually is ("Under 11 / AA"),
    which is the only confirmation available that the filters took effect.
    """
    expected = f"{config.DIVISION_LABEL} / {config.CATEGORY}"
    return [g.get("Div/Cat", "") for g in games if g.get("Div/Cat", "") != expected]


def scrape_schedule():
    """Scrape the schedule for the configured division."""
    driver = setup_driver()
    from_date, to_date = date_window()

    filters = {
        "division": config.DIVISION,
        "category": config.CATEGORY,
        "from_date": from_date,
        "to_date": to_date,
    }

    try:
        print("Navigating to GTHL schedule page...")
        driver.get(SCHEDULE_URL)
        wait = WebDriverWait(driver, 30)
        time.sleep(5)

        print("Switching to schedule iframe...")
        driver.switch_to.frame(
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, IFRAME_SELECTOR)))
        )
        time.sleep(5)

        print(f"Date range: {from_date} to {to_date}")
        select_option(driver, "ddlDiv", config.DIVISION)
        select_option(driver, "ddlCat", config.CATEGORY_VALUE)
        set_date(driver, "dpFrom", from_date)
        set_date(driver, "dpTo", to_date)

        try:
            driver.find_element(By.ID, "sche_btnSearch").click()
            print("Clicked search button")
            time.sleep(6)
        except Exception as e:
            print(f"Could not click search button: {e}")

        table = find_schedule_table(driver)
        if not table:
            with open("schedule_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return {
                "error": "No schedule table found",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filters": filters,
            }

        headers = read_headers(table)
        print(f"Headers: {headers}")

        games = parse_rows(table, headers)
        print(f"Extracted {len(games)} games")

        mismatched = wrong_division(games)
        if mismatched:
            return {
                "error": (
                    f"GTHL returned {len(mismatched)} games outside "
                    f"{config.DIVISION_LABEL} / {config.CATEGORY} "
                    f"(e.g. {mismatched[0]!r}). The division filter did not take "
                    "effect; refusing to publish another division's schedule."
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filters": filters,
            }

        return {
            "schedule": games,
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
    print("GTHL Schedule Scraper")
    print(f"Division: {config.DIVISION}, Category: {config.CATEGORY}")
    print("=" * 60)

    data = scrape_schedule()

    with open("schedule.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("\nData saved to schedule.json")

    if "error" in data:
        print(f"Error: {data['error']}")
        exit(1)

    count = len(data["schedule"])
    if count:
        print(f"Successfully scraped {count} games")
    else:
        # No games in the window is normal in the off-season.
        print(f"No games posted between {data['filters']['from_date']} "
              f"and {data['filters']['to_date']}")
    exit(0)


if __name__ == "__main__":
    main()

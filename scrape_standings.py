#!/usr/bin/env python3
"""
GTHL Standings Scraper
Scrapes standings for U10 AA West division from gthlcanada.com
"""

import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Configuration - hardcoded values as requested
DIVISION = "U10"
CATEGORY = "AA"
REGION = "West"
SEASON = "25-26"

def setup_driver():
    """Set up Chrome driver with headless options for GitHub Actions"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scrape_standings():
    """Scrape GTHL standings with the configured filters"""
    driver = setup_driver()

    try:
        # Navigate to main GTHL page first
        print(f"Navigating to GTHL standings page...")
        driver.get("https://gthlcanada.com/standing/")

        # Wait for page to load
        wait = WebDriverWait(driver, 20)

        print(f"Waiting for page and iframe to load...")
        time.sleep(5)

        # Find and switch to the iframe
        print("Switching to standings iframe...")
        iframe = wait.until(EC.presence_of_element_located((By.ID, "iframed-stats")))
        driver.switch_to.frame(iframe)
        print("Switched to iframe successfully")

        # Wait for iframe content to load
        time.sleep(5)

        # Now try to interact with filters inside the iframe
        try:
            from selenium.webdriver.support.ui import Select

            print(f"Looking for filter controls...")

            # Season dropdown - select 25-26 (should already be selected)
            try:
                season_select = driver.find_element(By.ID, "ddlSeason")
                season_dropdown = Select(season_select)
                season_dropdown.select_by_value("25-26")
                print(f"Selected season: 25-26")
                time.sleep(3)  # Wait for page reload
            except Exception as e:
                print(f"Could not find/select season dropdown: {e}")

            # Division dropdown - select U10
            try:
                div_select = driver.find_element(By.ID, "ddlDiv")
                div_dropdown = Select(div_select)
                div_dropdown.select_by_value("U10")
                print(f"Selected division: U10")
                time.sleep(3)  # Wait for page reload
            except Exception as e:
                print(f"Could not find/select division dropdown: {e}")

            # Category dropdown - select AA (A2)
            try:
                cat_select = driver.find_element(By.ID, "ddlCat")
                cat_dropdown = Select(cat_select)
                cat_dropdown.select_by_value("A2")
                print(f"Selected category: AA")
                time.sleep(3)  # Wait for page reload
            except Exception as e:
                print(f"Could not find/select category dropdown: {e}")

            # Region dropdown - select West
            try:
                region_select = driver.find_element(By.ID, "ddlRegion")
                region_dropdown = Select(region_select)
                region_dropdown.select_by_value("West")
                print(f"Selected region: West")
                time.sleep(3)  # Wait for page reload
            except Exception as e:
                print(f"Could not find/select region dropdown: {e}")

        except Exception as e:
            print(f"Note: Could not interact with filters: {e}")
            print("Attempting to scrape default standings...")

        # Wait for standings table to load
        print("Waiting for standings table...")
        time.sleep(3)

        # Try multiple common table selectors
        standings_data = []
        table = None

        # Try to find table by common selectors
        possible_selectors = [
            "table.standings",
            "table.wp-block-table",
            "div.standings-table table",
            "table",
            "div[class*='standing'] table"
        ]

        for selector in possible_selectors:
            try:
                tables = driver.find_elements(By.CSS_SELECTOR, selector)
                if tables:
                    table = tables[0]
                    print(f"Found table using selector: {selector}")
                    break
            except:
                continue

        if not table:
            # If no table found, save page source for debugging
            print("No table found. Saving page source...")
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            return {
                "error": "No standings table found",
                "timestamp": datetime.now().isoformat(),
                "filters": {
                    "division": DIVISION,
                    "category": CATEGORY,
                    "region": REGION,
                    "season": SEASON
                }
            }

        # Extract table headers
        headers = []
        try:
            header_row = table.find_element(By.TAG_NAME, "thead").find_element(By.TAG_NAME, "tr")
            headers = [th.text.strip() for th in header_row.find_elements(By.TAG_NAME, "th")]
        except:
            # Try to get headers from first row
            try:
                first_row = table.find_element(By.TAG_NAME, "tr")
                headers = [th.text.strip() for th in first_row.find_elements(By.TAG_NAME, "th")]
            except:
                headers = ["Position", "Team", "GP", "W", "L", "T", "OTL", "PTS", "GF", "GA", "DIFF"]

        print(f"Headers: {headers}")

        # Extract table rows
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row

        position = 1
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 3:  # At least team name and some stats
                    # Start with Position as the first key
                    row_data = {'Position': position}

                    # Try to extract team logo from the first cell (logo column)
                    try:
                        logo_img = cells[0].find_element(By.TAG_NAME, "img")
                        logo_src = logo_img.get_attribute("src")
                        if logo_src:
                            # Convert relative URL to absolute
                            if logo_src.startswith("Images/"):
                                logo_src = f"https://www.agilex.ca/SSP/{logo_src}"
                            row_data['Logo'] = logo_src
                    except:
                        row_data['Logo'] = None

                    # Add the rest of the data
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            key = headers[i]
                            # Skip empty column names
                            if key and key != '':
                                row_data[key] = cell.text.strip()

                    standings_data.append(row_data)
                    position += 1
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue

        print(f"Extracted {len(standings_data)} teams")

        result = {
            "standings": standings_data,
            "timestamp": datetime.now().isoformat(),
            "filters": {
                "division": DIVISION,
                "category": CATEGORY,
                "region": REGION,
                "season": SEASON
            }
        }

        return result

    except Exception as e:
        print(f"Error during scraping: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "filters": {
                "division": DIVISION,
                "category": CATEGORY,
                "region": REGION,
                "season": SEASON
            }
        }

    finally:
        driver.quit()

def main():
    """Main function"""
    print("=" * 60)
    print(f"GTHL Standings Scraper")
    print(f"Division: {DIVISION}, Category: {CATEGORY}")
    print(f"Region: {REGION}, Season: {SEASON}")
    print("=" * 60)

    data = scrape_standings()

    # Save to JSON file
    output_file = "standings.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nData saved to {output_file}")

    if "error" in data:
        print(f"Error: {data['error']}")
        exit(1)
    else:
        print(f"Successfully scraped {len(data['standings'])} teams")
        exit(0)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
GTHL Schedule Scraper
Scrapes schedule for U10 AA from gthlcanada.com
"""

import json
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

# Configuration
DIVISION = "U10"
CATEGORY = "AA"

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

def scrape_schedule():
    """Scrape GTHL schedule with the configured filters"""
    driver = setup_driver()

    try:
        # Navigate to main GTHL schedule page
        print(f"Navigating to GTHL schedule page...")
        driver.get("https://gthlcanada.com/schedule/")

        # Wait for page to load
        wait = WebDriverWait(driver, 20)

        print(f"Waiting for page and iframe to load...")
        time.sleep(5)

        # Find and switch to the iframe (uses different source than standings)
        print("Switching to schedule iframe...")
        iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='schedules.aspx']")))
        driver.switch_to.frame(iframe)
        print("Switched to iframe successfully")

        # Wait for iframe content to load
        time.sleep(5)

        # Calculate date range - start from yesterday to catch any recent games
        yesterday = datetime.now() - timedelta(days=1)
        three_months_later = yesterday + timedelta(days=90)

        # Format dates as DD-MMM-YYYY (e.g., 13-Nov-2025)
        from_date = yesterday.strftime("%d-%b-%Y")
        to_date = three_months_later.strftime("%d-%b-%Y")

        print(f"Date range: {from_date} to {to_date}")

        # Try to interact with filters inside the iframe
        try:
            print(f"Looking for filter controls...")

            # Division dropdown - select U10
            try:
                div_select = driver.find_element(By.ID, "ddlDiv")
                div_dropdown = Select(div_select)
                div_dropdown.select_by_value("U10")
                print(f"Selected division: U10")
                time.sleep(3)
            except Exception as e:
                print(f"Could not find/select division dropdown: {e}")

            # Category dropdown - select AA (A2)
            try:
                cat_select = driver.find_element(By.ID, "ddlCat")
                cat_dropdown = Select(cat_select)
                cat_dropdown.select_by_value("A2")
                print(f"Selected category: AA")
                time.sleep(3)
            except Exception as e:
                print(f"Could not find/select category dropdown: {e}")

            # From date field
            try:
                from_date_field = driver.find_element(By.ID, "dpFrom")
                from_date_field.clear()
                from_date_field.send_keys(from_date)
                print(f"Set from date: {from_date}")
                time.sleep(2)
            except Exception as e:
                print(f"Could not find/set from date: {e}")

            # To date field
            try:
                to_date_field = driver.find_element(By.ID, "dpTo")
                to_date_field.clear()
                to_date_field.send_keys(to_date)
                print(f"Set to date: {to_date}")
                time.sleep(2)
            except Exception as e:
                print(f"Could not find/set to date: {e}")

            # Click search/submit button
            try:
                search_btn = driver.find_element(By.ID, "sche_btnSearch")
                search_btn.click()
                print("Clicked search button")
                time.sleep(5)
            except Exception as e:
                print(f"Could not find/click search button: {e}")

        except Exception as e:
            print(f"Note: Could not interact with filters: {e}")
            print("Attempting to scrape default schedule...")

        # Wait for schedule table to load
        print("Waiting for schedule table...")
        time.sleep(3)

        # Try to find schedule table
        schedule_data = []
        table = None

        possible_selectors = [
            "table.schedule",
            "table.wp-block-table",
            "div.schedule-table table",
            "table",
            "div[class*='schedule'] table"
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
            print("No table found. Saving page source...")
            with open("schedule_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            return {
                "error": "No schedule table found",
                "timestamp": datetime.now().isoformat(),
                "filters": {
                    "division": DIVISION,
                    "category": CATEGORY,
                    "from_date": from_date,
                    "to_date": to_date
                }
            }

        # Extract table headers
        headers = []
        try:
            header_row = table.find_element(By.TAG_NAME, "thead").find_element(By.TAG_NAME, "tr")
            headers = [th.text.strip() for th in header_row.find_elements(By.TAG_NAME, "th")]
        except:
            try:
                first_row = table.find_element(By.TAG_NAME, "tr")
                headers = [th.text.strip() for th in first_row.find_elements(By.TAG_NAME, "th")]
            except:
                headers = ["Date", "Time", "Home Team", "Away Team", "Location", "Status"]

        print(f"Headers: {headers}")

        # Extract table rows
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row

        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 3:
                    row_data = {}
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            key = headers[i]
                            if key and key != '':
                                row_data[key] = cell.text.strip()

                    # Only add if we have data
                    if row_data:
                        schedule_data.append(row_data)
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue

        print(f"Extracted {len(schedule_data)} games")

        result = {
            "schedule": schedule_data,
            "timestamp": datetime.now().isoformat(),
            "filters": {
                "division": DIVISION,
                "category": CATEGORY,
                "from_date": from_date,
                "to_date": to_date
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
                "from_date": "",
                "to_date": ""
            }
        }

    finally:
        driver.quit()

def main():
    """Main function"""
    print("=" * 60)
    print(f"GTHL Schedule Scraper")
    print(f"Division: {DIVISION}, Category: {CATEGORY}")
    print("=" * 60)

    data = scrape_schedule()

    # Save to JSON file
    output_file = "schedule.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nData saved to {output_file}")

    if "error" in data:
        print(f"Error: {data['error']}")
        exit(1)
    else:
        print(f"Successfully scraped {len(data['schedule'])} games")
        exit(0)

if __name__ == "__main__":
    main()

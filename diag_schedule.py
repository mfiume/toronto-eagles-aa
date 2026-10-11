"""Temporary: show what the schedule table's cells contain. Read-only."""
from selenium.webdriver.common.by import By
import scrape_schedule as s

orig = s.parse_rows

def parse_rows(table, headers):
    rows = table.find_elements(By.TAG_NAME, "tr")
    print("ROWS", len(rows))
    for r in rows[:4]:
        cells = r.find_elements(By.TAG_NAME, "td") or r.find_elements(By.TAG_NAME, "th")
        print("ROW", [(c.text, c.get_attribute("textContent").strip(), c.is_displayed()) for c in cells])
    if len(rows) > 1:
        print("HTML", rows[1].get_attribute("outerHTML")[:3000])
    return orig(table, headers)

s.parse_rows = parse_rows
result = s.scrape_schedule()
print("ERROR", result.get("error"))
print("SAMPLE", result.get("schedule", [])[:2])

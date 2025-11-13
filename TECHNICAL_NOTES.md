# Technical Notes

## Important: Website Scraping Considerations

The GTHL website at https://gthlcanada.com/standing/ uses JavaScript to load and filter standings data. This means:

### Current Implementation

The scraper (`scrape_standings.py`) uses **Selenium with Chrome** to:
1. Load the page with a headless browser
2. Wait for JavaScript to execute
3. Interact with filter controls
4. Extract the standings table

### Potential Issues & Solutions

#### 1. **Filter Selectors May Need Adjustment**

The current implementation uses generic XPath selectors:
```python
division_filter = wait.until(
    EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{DIVISION}')]"))
)
```

**Why this might fail:**
- The website may use dropdown menus, buttons, or custom controls
- Text matching may not work if filters are icons or abbreviations
- Multiple elements might match the text

**How to fix:**
1. Run the scraper locally: `python3 test_scraper.py`
2. Check the generated `page_source.html` file
3. Find the actual HTML structure of the filter controls
4. Update the selectors in `scrape_standings.py`

Example alternative selectors:
```python
# If filters are in a select dropdown
division_select = Select(driver.find_element(By.ID, "division-filter"))
division_select.select_by_visible_text("U10")

# If filters are data attributes
division_filter = driver.find_element(By.CSS_SELECTOR, "[data-division='U10']")

# If filters are specific classes
division_filter = driver.find_element(By.CSS_SELECTOR, ".filter-division .option-u10")
```

#### 2. **Table Structure May Vary**

The scraper tries multiple common table selectors:
```python
possible_selectors = [
    "table.standings",
    "table.wp-block-table",
    "div.standings-table table",
    "table",
    "div[class*='standing'] table"
]
```

If none work, you may need to:
- Inspect the actual HTML structure
- Add the correct selector to the list
- Or extract data from non-table elements (divs, cards, etc.)

#### 3. **Rate Limiting / Bot Detection**

Some websites block automated scrapers. If you encounter issues:

**Add delays:**
```python
time.sleep(2)  # Wait between actions
```

**Add user agent:**
```python
chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
```

**Add cookies/session management** if needed.

#### 4. **Dynamic Content Loading**

If data loads via AJAX/API calls, you might be able to:

**Option A: Intercept network requests**
```python
# Capture API calls made by the page
driver.execute_cdp_cmd('Network.enable', {})
# Extract data from API responses
```

**Option B: Find the API endpoint directly**
- Open browser DevTools → Network tab
- Load gthlcanada.com/standing/
- Look for XHR/Fetch requests that return JSON data
- Use `requests` library instead of Selenium (faster!)

Example:
```python
import requests
response = requests.get("https://gthlcanada.com/api/standings", params={
    "division": "U10",
    "category": "AA",
    "region": "West",
    "season": "25-26"
})
data = response.json()
```

### Testing Locally

Before deploying to GitHub Actions:

1. **Install dependencies:**
   ```bash
   cd ~/gthl-standings-tracker
   pip3 install -r requirements.txt
   ```

2. **Run test script:**
   ```bash
   python3 test_scraper.py
   ```

3. **Check output:**
   - If successful: You'll see team data
   - If failed: Check `page_source.html` to debug

4. **View generated page:**
   ```bash
   open index.html  # macOS
   # or
   xdg-open index.html  # Linux
   ```

### GitHub Actions Environment

The workflow installs Chrome automatically:
```yaml
- name: Install Chrome and ChromeDriver
  run: |
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
    sudo apt-get update
    sudo apt-get install -y google-chrome-stable
```

Selenium 4.15+ includes `selenium-manager` which automatically downloads ChromeDriver.

### Debugging Failed Runs

If the GitHub Action fails:

1. **Check the logs:**
   - Go to Actions tab → Click on the failed run → Click on "scrape" job
   - Read the output for error messages

2. **Common issues:**
   - Chrome installation failed → Check Ubuntu package availability
   - Timeout waiting for elements → Increase wait times
   - Table not found → Update selectors
   - Permission denied → Check workflow permissions

3. **Download artifacts:**
   If the scraper saves `page_source.html`, you can add this to the workflow:
   ```yaml
   - name: Upload debug files
     if: failure()
     uses: actions/upload-artifact@v3
     with:
       name: debug-files
       path: page_source.html
   ```

### Alternative Approaches

If Selenium proves too complex or unreliable:

#### 1. **Use Playwright**
More modern browser automation:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://gthlcanada.com/standing/")
    # ... interact with page
```

#### 2. **Use API if available**
Fastest and most reliable if GTHL has a public API.

#### 3. **Manual updates with easy interface**
If scraping proves too difficult, create a simple form where someone can paste the standings data manually.

### Maintenance

The scraper may need updates when:
- GTHL website redesigns
- Filter options change
- Table structure changes
- New seasons are added

Check the GitHub Actions logs periodically to ensure it's working.

---

## Performance Notes

- **Selenium scrape time:** ~10-20 seconds
- **HTML generation:** <1 second
- **GitHub Action total:** ~2-3 minutes (including setup)
- **GitHub Pages update:** ~1-2 minutes after commit

Total latency from scrape to published page: ~5 minutes

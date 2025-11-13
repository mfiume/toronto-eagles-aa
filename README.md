# Toronto Eagles U10 AA - Team Hub

Automated team hub for the Toronto Eagles U10 AA hockey team, tracking standings and schedule from the GTHL (Greater Toronto Hockey League).

## Features

- 🦅 **Toronto Eagles Focused**: Team highlighted in standings view
- 🤖 **Automated Nightly Updates**: Runs automatically every night at 2 AM ET
- 📊 **West Region Standings**: U10 AA West division standings with team logos
- 🎯 **Modern Design**: Clean, responsive black and white interface
- 🚀 **GitHub Pages**: Hosted automatically, no server required
- 📅 **Schedule Tracking**: (Coming soon) Team schedule and game times

## View Live Page

Visit: **https://mfiume.github.io/toronto-eagles-u10aa/**

## Configuration

The scraper is pre-configured with:
- **Season**: 25-26
- **Division**: U10 (Under 10)
- **Category**: AA
- **Region**: West

These values are hardcoded in `scrape_standings.py` and can be modified if needed.

**Note**: The GTHL website uses an iframe with dropdowns for filtering:
- Season dropdown (`ddlSeason`): Options like "25-26", "24-25", etc.
- Division dropdown (`ddlDiv`): Values like "U10" for Under 10
- Category dropdown (`ddlCat`): Values like "A2" for AA, "A3" for AAA, "A1" for A
- Region dropdown (`ddlRegion`): "East" or "West"

## Setup Instructions

### 1. Create GitHub Repository

1. Create a new GitHub repository (e.g., `gthl-standings`)
2. Clone this repository to your local machine
3. Push all files to your GitHub repository

```bash
git init
git add .
git commit -m "Initial commit: GTHL standings tracker"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/gthl-standings.git
git push -u origin main
```

### 2. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages**
3. Under "Build and deployment":
   - Source: **Deploy from a branch**
   - Branch: **main** / **root**
4. Click **Save**
5. Your site will be published at: `https://YOUR_USERNAME.github.io/gthl-standings/`

### 3. Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. If prompted, click **"I understand my workflows, go ahead and enable them"**
3. The workflow will run automatically every night at 2 AM EST

### 4. Manual Trigger (Optional)

You can manually trigger the scraper anytime:

1. Go to **Actions** tab
2. Click **"Scrape GTHL Standings"** workflow
3. Click **"Run workflow"** → **"Run workflow"**

## How It Works

1. **Scraper Script** (`scrape_standings.py`):
   - Uses Selenium to navigate to gthlcanada.com/standing/
   - Applies filters (Division, Category, Region, Season)
   - Extracts standings table data
   - Saves to `standings.json`

2. **HTML Generator** (`generate_html.py`):
   - Reads `standings.json`
   - Generates beautiful HTML page (`index.html`)
   - Includes timestamp and filter information

3. **GitHub Action** (`.github/workflows/scrape-standings.yml`):
   - Runs nightly at 2 AM EST (7 AM UTC)
   - Installs dependencies and Chrome browser
   - Executes scraper and HTML generator
   - Commits and pushes changes if data updated

4. **GitHub Pages**:
   - Automatically publishes `index.html`
   - Updates reflect within minutes of commit

## Files

```
gthl-standings-tracker/
├── scrape_standings.py         # Main scraper script
├── generate_html.py             # HTML page generator
├── requirements.txt             # Python dependencies
├── .github/
│   └── workflows/
│       └── scrape-standings.yml # GitHub Action workflow
├── README.md                    # This file
├── standings.json               # Generated standings data (after first run)
└── index.html                   # Generated web page (after first run)
```

## Troubleshooting

### Scraper Fails to Find Data

The GTHL website may change its structure. To debug:

1. Check the GitHub Actions logs for errors
2. The scraper saves `page_source.html` when it can't find the table
3. Update the selectors in `scrape_standings.py` if needed

### GitHub Pages Not Updating

- Ensure GitHub Pages is enabled in Settings → Pages
- Check that `index.html` exists in the repository root
- GitHub Pages may take a few minutes to update after commit

### Action Permission Denied

If the GitHub Action can't commit changes:

1. Go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select **"Read and write permissions"**
3. Click **Save**

## Customization

### Change Filter Values

Edit `scrape_standings.py`:

```python
# Configuration - hardcoded values as requested
DIVISION = "U10"     # Change division
CATEGORY = "AA"      # Change category
REGION = "West"      # Change region
SEASON = "25-26"     # Change season
```

### Change Schedule

Edit `.github/workflows/scrape-standings.yml`:

```yaml
schedule:
  - cron: '0 7 * * *'  # 7 AM UTC = 2 AM EST
  # Change to run at different time
```

Cron format: `minute hour day month weekday`

### Customize HTML Styling

Edit the `<style>` section in `generate_html.py` to change:
- Colors
- Fonts
- Layout
- Responsive breakpoints

## License

MIT License - Feel free to use and modify for your own purposes.

## Credits

Data sourced from [GTHL Canada](https://gthlcanada.com/)

# Quick Setup Guide

Follow these steps to deploy your GTHL standings tracker:

## Step 1: Create GitHub Repository

1. Go to [GitHub](https://github.com) and create a new repository
   - Name: `gthl-standings` (or any name you prefer)
   - Visibility: **Public** (required for free GitHub Pages)
   - Don't initialize with README (we have our own)

## Step 2: Push Code to GitHub

```bash
cd ~/gthl-standings-tracker

# Initialize git
git init
git add .
git commit -m "Initial commit: GTHL standings tracker"

# Connect to your GitHub repository (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Enable GitHub Actions Permissions

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. In the left sidebar, click **Actions** → **General**
4. Scroll to "Workflow permissions"
5. Select **"Read and write permissions"**
6. Check **"Allow GitHub Actions to create and approve pull requests"**
7. Click **Save**

## Step 4: Enable GitHub Pages

1. Still in **Settings**, click **Pages** in the left sidebar
2. Under "Build and deployment":
   - Source: **Deploy from a branch**
   - Branch: **main**
   - Folder: **/ (root)**
3. Click **Save**
4. Wait 1-2 minutes, then refresh the page
5. You'll see: **"Your site is live at https://YOUR_USERNAME.github.io/REPO_NAME/"**

## Step 5: Run the First Scrape

You can either:

### Option A: Wait for Nightly Run
The action will automatically run at 2 AM EST every night.

### Option B: Trigger Manually Now
1. Go to **Actions** tab in your repository
2. Click **"Scrape GTHL Standings"** in the left sidebar
3. Click **"Run workflow"** button (top right)
4. Select branch **main**
5. Click green **"Run workflow"** button
6. Wait ~2 minutes for it to complete
7. Check your GitHub Pages URL to see the results!

## Step 6: Verify It's Working

1. Visit your GitHub Pages URL
2. You should see a beautiful standings table
3. Check that the filters show: U10, AA, West, 25-26

## Troubleshooting

### "Actions are disabled in this repository"
- Go to **Actions** tab → Click "Enable workflows"

### "Push declined due to repository rule violations"
- Go to Settings → Actions → General
- Enable "Read and write permissions"

### GitHub Pages shows 404
- Wait a few minutes after enabling (can take up to 10 minutes)
- Ensure `index.html` exists in repository root
- Check Settings → Pages shows "Your site is published"

### Scraper finds no data
- The GTHL website may require specific interaction
- Check Actions logs for errors
- The script includes fallback error handling

## What Happens Next?

✅ Every night at 2 AM EST, the GitHub Action will:
1. Scrape the latest standings
2. Generate updated HTML
3. Commit changes (if any)
4. GitHub Pages automatically publishes updates

✅ You'll always have the latest standings without any manual work!

## Customizing

Want to track a different division? Edit `scrape_standings.py`:

```python
DIVISION = "U10"     # Change this
CATEGORY = "AA"      # Change this
REGION = "West"      # Change this
SEASON = "25-26"     # Change this
```

Then commit and push the changes.

---

**Need Help?** Check the detailed README.md or open an issue in the repository.

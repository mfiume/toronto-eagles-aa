#!/usr/bin/env python3
"""
Test script to verify the scraper can access GTHL website
Run this locally before deploying to GitHub
"""

import sys
from scrape_standings import scrape_standings

def main():
    print("Testing GTHL standings scraper...")
    print("-" * 60)

    try:
        data = scrape_standings()

        if "error" in data:
            print(f"\n❌ Error occurred: {data['error']}")
            print("\nThis might be because:")
            print("- The website structure has changed")
            print("- The filters don't match available options")
            print("- The website requires JavaScript interaction")
            print("\nCheck page_source.html (if generated) to debug.")
            return 1
        else:
            standings = data.get("standings", [])
            print(f"\n✅ Success! Found {len(standings)} teams")

            if standings:
                print("\nFirst team:")
                for key, value in standings[0].items():
                    print(f"  {key}: {value}")
            else:
                print("\n⚠️  Warning: No teams found with current filters")
                print("   Division: U10, Category: AA, Region: West, Season: 25-26")

            return 0

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

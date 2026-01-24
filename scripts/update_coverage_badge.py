#!/usr/bin/env python3
"""Generate a coverage badge using shields.io and save it to the repo."""

import json
import urllib.request
import sys
from pathlib import Path

def get_coverage_percentage():
    """Extract coverage percentage from pytest coverage.json report."""
    coverage_json = Path("coverage.json")
    
    if not coverage_json.exists():
        print("Error: coverage.json not found")
        return None
    
    try:
        with open(coverage_json) as f:
            data = json.load(f)
        
        # Extract the overall coverage percentage
        coverage_pct = data.get("totals", {}).get("percent_covered", 0)
        return round(coverage_pct, 1)
    except Exception as e:
        print(f"Error reading coverage.json: {e}")
        return None

def get_badge_color(coverage_pct):
    """Return color based on coverage percentage."""
    if coverage_pct >= 90:
        return "brightgreen"
    elif coverage_pct >= 80:
        return "green"
    elif coverage_pct >= 70:
        return "yellowgreen"
    elif coverage_pct >= 60:
        return "yellow"
    elif coverage_pct >= 50:
        return "orange"
    else:
        return "red"

def download_badge(coverage_pct, output_path):
    """Download badge from shields.io and save to file."""
    color = get_badge_color(coverage_pct)
    url = f"https://img.shields.io/badge/coverage-{coverage_pct}%25-{color}.svg"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            badge_content = response.read()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(badge_content)
        
        print(f"Coverage badge saved: {output_path}")
        return True
    except Exception as e:
        print(f"Error downloading badge: {e}")
        return False

def main():
    coverage_pct = get_coverage_percentage()
    
    if coverage_pct is None:
        sys.exit(1)
    
    print(f"Coverage: {coverage_pct}%")
    
    badge_path = Path(".github/coverage-badge.svg")
    if download_badge(coverage_pct, badge_path):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

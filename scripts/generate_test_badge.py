#!/usr/bin/env python3
"""Generate a test count badge as SVG."""
# ruff: noqa: E501

import sys
from pathlib import Path


def generate_badge_svg(count, output_path):
    """Generate SVG badge with test count."""
    svg_template = '''<svg xmlns="http://www.w3.org/2000/svg" width="88" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="88" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h41v20H0z"/>
    <path fill="#007ec6" d="M41 0h47v20H41z"/>
    <path fill="url(#b)" d="M0 0h88v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="20.5" y="15" fill="#010101" fill-opacity=".3">tests</text>
    <text x="20.5" y="14">tests</text>
    <text x="64.5" y="15" fill="#010101" fill-opacity=".3">{count}</text>
    <text x="64.5" y="14">{count}</text>
  </g>
</svg>'''

    svg_content = svg_template.format(count=count)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(svg_content)

    print(f"Test count badge saved: {output_path}")
    return True


def main():
    """Main function to generate test count badge."""
    # For now, we'll get test count from command line argument
    # This will be passed from the workflow after pytest runs
    if len(sys.argv) < 2:
        print("Usage: generate_test_badge.py <test_count>")
        sys.exit(1)

    try:
        test_count = int(sys.argv[1])
    except ValueError:
        print("Error: test_count must be an integer")
        sys.exit(1)

    badge_path = Path(".github/tests-badge.svg")
    if generate_badge_svg(test_count, badge_path):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

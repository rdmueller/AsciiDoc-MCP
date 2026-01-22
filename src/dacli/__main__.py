"""Allow running as python -m dacli."""

from dacli.main import main

if __name__ == "__main__":
    raise SystemExit(main())

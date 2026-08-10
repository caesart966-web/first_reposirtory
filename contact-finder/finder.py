"""Точка входа CLI.

    python finder.py --input companies.xlsx --output result.xlsx \
                     --sources all --threads 10 --depth full
"""
from ui.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

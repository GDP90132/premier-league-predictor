import io
import json
import sys
import time
from datetime import date

import pandas as pd
import requests

from cleaning import clean_matches
from db import count_matches, upsert_matches, upsert_raw

BASE_URL = "https://www.football-data.co.uk/mmz4281"
LEAGUES = {"E0": "Premier League", "SP1": "La Liga", "D1": "Bundesliga",
           "I1": "Serie A", "F1": "Ligue 1"}
REQUIRED = ["Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]


def current_season_code(today: date | None = None) -> str:
    """A season starts in July/August: Nov 2026 -> '2627', March 2027 -> '2627'."""
    today = today or date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def download(url: str, tries: int = 3) -> bytes | None:
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.content
        except requests.RequestException as e:
            print(f"  attempt {attempt} failed: {e}")
            time.sleep(2 * attempt)
    return None


def main() -> None:
    season = current_season_code()
    before = count_matches()
    failures = 0
    print(f"season {season}, matches in database before: {before}")

    for code, league in LEAGUES.items():
        url = f"{BASE_URL}/{season}/{code}.csv"
        content = download(url)
        if content is None:
            print(f"{league}: download failed")
            failures += 1
            continue

        raw = pd.read_csv(io.BytesIO(content)).dropna(how="all")
        missing = [c for c in REQUIRED if c not in raw.columns]
        if missing:
            print(f"{league}: file is missing columns {missing}, skipped")
            failures += 1
            continue

        # raw layer: every original row, untouched
        filename = f"{season}_{code}.csv"
        payloads = json.loads(raw.to_json(orient="records"))
        upsert_raw([
            (filename, int(idx), season, league, {
             k: v for k, v in rec.items() if v is not None})
            for idx, rec in zip(raw.index, payloads)
        ])

        # clean layer
        cleaned = clean_matches(raw, league, season)
        upsert_matches(cleaned)
        print(f"{league}: {len(cleaned)} finished matches in file")
        time.sleep(1)

    after = count_matches()
    print(f"matches in database after: {after} (new: {after - before})")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()

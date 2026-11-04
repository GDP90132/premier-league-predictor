import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://www.football-data.co.uk/mmz4281"
LEAGUES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "D1": "Bundesliga",
    "I1": "Serie A",
    "F1": "Ligue 1",
}
# 2005 -> "0506", ..., 2026 -> "2627"
SEASONS = [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(2005, 2027)]

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

frames = []
for season in SEASONS:
    for code, league_name in LEAGUES.items():
        url = f"{BASE_URL}/{season}/{code}.csv"
        path = RAW_DIR / f"{season}_{code}.csv"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            path.write_bytes(response.content)
            df = pd.read_csv(path)
        except Exception as e:
            print(f"FAILED {season} {code}: {e}")
            continue
        df["season"] = season
        df["league"] = league_name
        frames.append(df)
        time.sleep(1)

all_matches = pd.concat(frames, ignore_index=True)
all_matches.to_csv("data/all_matches_raw.csv", index=False)

print(all_matches.shape)
print(all_matches.groupby("league").size())

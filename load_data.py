import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

load_dotenv("api.env")
conn = psycopg2.connect(os.getenv("DATABASE_URL"))

LEAGUES = {"E0": "Premier League", "SP1": "La Liga", "D1": "Bundesliga",
           "I1": "Serie A", "F1": "Ligue 1"}


def py(v):
    """Turn pandas/numpy values into plain Python values that psycopg2 accepts."""
    if pd.isna(v):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, pd.Timestamp):
        return v.date()
    return v


# ---------- 1. raw layer: every original row, untouched ----------
raw_rows = []
for path in sorted(Path("data/raw").glob("*.csv")):
    season, code = path.stem.split("_")
    df = pd.read_csv(path).dropna(how="all")  # index = original row number
    for idx, rec in zip(df.index, json.loads(df.to_json(orient="records"))):
        payload = {k: v for k, v in rec.items() if v is not None}
        raw_rows.append((path.name, int(idx), season,
                        LEAGUES[code], Json(payload)))

with conn, conn.cursor() as cur:
    execute_values(cur, """
        INSERT INTO raw_matches (source_file, row_num, season, league, payload)
        VALUES %s
        ON CONFLICT (source_file, row_num) DO UPDATE
        SET payload = EXCLUDED.payload, loaded_at = now()
    """, raw_rows, page_size=500)
print("raw rows upserted:", len(raw_rows))

# ---------- 2. clean layer: typed, renamed columns ----------
df = pd.read_csv("data/matches_clean.csv",
                 parse_dates=["Date"], dtype={"season": str})
RENAME = {
    "Div": "div", "Date": "match_date", "HomeTeam": "home_team", "AwayTeam": "away_team",
    "FTHG": "home_goals", "FTAG": "away_goals", "FTR": "result",
    "HTHG": "ht_home_goals", "HTAG": "ht_away_goals", "HTR": "ht_result",
    "HS": "home_shots", "AS": "away_shots", "HST": "home_sot", "AST": "away_sot",
    "HC": "home_corners", "AC": "away_corners", "HF": "home_fouls", "AF": "away_fouls",
    "HY": "home_yellows", "AY": "away_yellows", "HR": "home_reds", "AR": "away_reds",
    "B365H": "b365_home", "B365D": "b365_draw", "B365A": "b365_away",
}
df = df.rename(columns=RENAME)
COLS = ["match_id", "div", "league", "season", "match_date", "home_team", "away_team",
        "home_goals", "away_goals", "result", "ht_home_goals", "ht_away_goals", "ht_result",
        "home_shots", "away_shots", "home_sot", "away_sot", "home_corners", "away_corners",
        "home_fouls", "away_fouls", "home_yellows", "away_yellows", "home_reds", "away_reds",
        "b365_home", "b365_draw", "b365_away"]
INT_COLS = [c for c in COLS if c.startswith(("home_", "away_", "ht_home", "ht_away"))
            and not c.endswith("_team") and not c.startswith(("b365",))]

rows = []
for rec in df[COLS].itertuples(index=False):
    row = [py(v) for v in rec]
    for i, c in enumerate(COLS):
        if c in INT_COLS and row[i] is not None:
            row[i] = int(row[i])
    rows.append(tuple(row))

update_cols = [c for c in COLS if c != "match_id"]
sql = f"""
    INSERT INTO matches ({", ".join(COLS)}) VALUES %s
    ON CONFLICT (match_id) DO UPDATE SET
    {", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)}, updated_at = now()
"""
with conn, conn.cursor() as cur:
    execute_values(cur, sql, rows, page_size=1000)
print("matches upserted:", len(rows))

# ---------- 3. checks ----------
with conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM raw_matches")
    print("raw_matches rows:", cur.fetchone()[0])
    cur.execute(
        "SELECT league, count(*) FROM matches GROUP BY league ORDER BY league")
    print("matches by league:", cur.fetchall())
    cur.execute("SELECT count(*), min(match_date), max(match_date) FROM matches")
    print("matches total / first / last:", cur.fetchone())
    cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
    print("database size:", cur.fetchone()[0])
conn.close()

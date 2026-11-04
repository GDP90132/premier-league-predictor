import os
from contextlib import contextmanager
import numpy as np
from psycopg2.extras import Json, execute_values
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv("api.env")


def _url(pooled: bool) -> str:
    """Pick the connection string. Pooled is for the API/app, direct is for setup and bulk loads."""
    url = None
    if pooled:
        url = os.getenv("DATABASE_URL_POOLED")
    return url or os.getenv("DATABASE_URL")


@contextmanager
def get_conn(pooled: bool = False):
    """Open a connection, commit on success, roll back on error, always close."""
    conn = psycopg2.connect(_url(pooled))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_df(sql: str, params=None, pooled: bool = False) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame. Values go in `params`, never into the SQL string."""
    with get_conn(pooled) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


# ---------- queries ----------

def get_matches_for_features() -> pd.DataFrame:
    """All matches, with the same column names the CSV had, so features.py barely changes."""
    sql = """
        SELECT match_id, div AS "Div", league, season, match_date AS "Date",
               home_team AS "HomeTeam", away_team AS "AwayTeam",
               home_goals AS "FTHG", away_goals AS "FTAG", result AS "FTR",
               ht_home_goals AS "HTHG", ht_away_goals AS "HTAG", ht_result AS "HTR",
               home_shots AS "HS", away_shots AS "AS",
               home_sot AS "HST", away_sot AS "AST",
               home_corners AS "HC", away_corners AS "AC",
               home_fouls AS "HF", away_fouls AS "AF",
               home_yellows AS "HY", away_yellows AS "AY",
               home_reds AS "HR", away_reds AS "AR",
               b365_home::float AS "B365H", b365_draw::float AS "B365D",
               b365_away::float AS "B365A"
        FROM matches
        ORDER BY match_date, match_id
    """
    df = query_df(sql)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def get_teams(league: str | None = None, pooled: bool = True) -> list[str]:
    """Team names, optionally for one league, sorted."""
    sql = "SELECT DISTINCT home_team FROM matches"
    params = None
    if league:
        sql += " WHERE league = %s"
        params = (league,)
    sql += " ORDER BY home_team"
    return query_df(sql, params, pooled)["home_team"].tolist()


def get_recent_matches(team: str, n: int = 10, pooled: bool = True) -> pd.DataFrame:
    """A team's last n matches (home or away), newest first."""
    sql = """
        SELECT match_date, league, home_team, away_team, home_goals, away_goals, result
        FROM matches
        WHERE home_team = %s OR away_team = %s
        ORDER BY match_date DESC
        LIMIT %s
    """
    return query_df(sql, (team, team, n), pooled)


def get_latest_match_date(pooled: bool = True):
    """Most recent match date in the database (the update job uses this)."""
    return query_df("SELECT max(match_date) AS d FROM matches", pooled=pooled)["d"].iloc[0]


if __name__ == "__main__":
    print("latest match:", get_latest_match_date())
    print("Premier League teams:", len(get_teams("Premier League")))
    print(get_recent_matches("Arsenal", 5))
    print("feature frame:", get_matches_for_features().shape)

MATCH_COLS = [
    "match_id", "div", "league", "season", "match_date", "home_team", "away_team",
    "home_goals", "away_goals", "result", "ht_home_goals", "ht_away_goals", "ht_result",
    "home_shots", "away_shots", "home_sot", "away_sot", "home_corners", "away_corners",
    "home_fouls", "away_fouls", "home_yellows", "away_yellows", "home_reds", "away_reds",
    "b365_home", "b365_draw", "b365_away",
]
TEXT_COLS = {"match_id", "div", "league", "season", "home_team", "away_team",
             "result", "ht_result", "match_date"}
ODDS_COLS = {"b365_home", "b365_draw", "b365_away"}


def _py(v):
    """Plain Python value for psycopg2 (NaN -> None, numpy -> int/float, Timestamp -> date)."""
    if v is None or pd.isna(v):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, pd.Timestamp):
        return v.date()
    return v


def count_matches() -> int:
    return int(query_df("SELECT count(*) AS n FROM matches")["n"].iloc[0])


def upsert_raw(rows: list) -> None:
    """rows: (source_file, row_num, season, league, payload_dict)"""
    data = [(a, b, c, d, Json(e)) for a, b, c, d, e in rows]
    sql = """
        INSERT INTO raw_matches (source_file, row_num, season, league, payload)
        VALUES %s
        ON CONFLICT (source_file, row_num) DO UPDATE
        SET payload = EXCLUDED.payload, loaded_at = now()
    """
    with get_conn() as conn, conn.cursor() as cur:
        execute_values(cur, sql, data, page_size=500)


def upsert_matches(df: pd.DataFrame) -> None:
    """df must have the MATCH_COLS columns. Inserts new matches, updates existing ones."""
    rows = []
    for rec in df[MATCH_COLS].itertuples(index=False):
        row = []
        for col, v in zip(MATCH_COLS, rec):
            v = _py(v)
            if v is not None and col not in TEXT_COLS and col not in ODDS_COLS:
                v = int(v)
            row.append(v)
        rows.append(tuple(row))
    updates = ", ".join(
        f"{c} = EXCLUDED.{c}" for c in MATCH_COLS if c != "match_id")
    sql = f"""
        INSERT INTO matches ({", ".join(MATCH_COLS)}) VALUES %s
        ON CONFLICT (match_id) DO UPDATE SET {updates}, updated_at = now()
    """
    with get_conn() as conn, conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)

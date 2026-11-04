import os

import psycopg2
from dotenv import load_dotenv

load_dotenv("api.env")

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_matches (
    source_file TEXT        NOT NULL,
    row_num     INTEGER     NOT NULL,
    season      TEXT        NOT NULL,
    league      TEXT        NOT NULL,
    payload     JSONB       NOT NULL,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source_file, row_num)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id        TEXT PRIMARY KEY,
    div             TEXT    NOT NULL,
    league          TEXT    NOT NULL,
    season          TEXT    NOT NULL,
    match_date      DATE    NOT NULL,
    home_team       TEXT    NOT NULL,
    away_team       TEXT    NOT NULL,
    home_goals      INTEGER,
    away_goals      INTEGER,
    result          CHAR(1) CHECK (result IN ('H', 'D', 'A')),
    ht_home_goals   INTEGER,
    ht_away_goals   INTEGER,
    ht_result       CHAR(1),
    home_shots      INTEGER,
    away_shots      INTEGER,
    home_sot        INTEGER,
    away_sot        INTEGER,
    home_corners    INTEGER,
    away_corners    INTEGER,
    home_fouls      INTEGER,
    away_fouls      INTEGER,
    home_yellows    INTEGER,
    away_yellows    INTEGER,
    home_reds       INTEGER,
    away_reds       INTEGER,
    b365_home       NUMERIC(6, 2),
    b365_draw       NUMERIC(6, 2),
    b365_away       NUMERIC(6, 2),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches (match_date);
CREATE INDEX IF NOT EXISTS idx_matches_home ON matches (home_team);
CREATE INDEX IF NOT EXISTS idx_matches_away ON matches (away_team);
"""

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
with conn, conn.cursor() as cur:
    cur.execute(SCHEMA)
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    )
    print("tables:", [r[0] for r in cur.fetchall()])
conn.close()

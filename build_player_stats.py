"""Turn the Transfermarkt DuckDB file into one small table of player stats per season,
split by competition (league, Champions League, Europa League, domestic cups).

Step 1 (safe, changes nothing):   python3 build_player_stats.py
Step 2 (writes to your database): python3 build_player_stats.py --load

--load creates ONE new table, player_season_stats, and refills it each time.
It does not touch any of your other tables.

Options:
  --duckdb PATH   default data/transfermarkt-datasets.duckdb
"""
import argparse
import os
import pathlib
import sys
from collections import Counter, defaultdict

import duckdb

LEAGUES = {"GB1": "Premier League", "ES1": "La Liga", "L1": "Bundesliga", "IT1": "Serie A", "FR1": "Ligue 1"}
NICE_NAMES = {
    **LEAGUES,
    "CL": "Champions League", "EL": "Europa League",
    "FAC": "FA Cup", "CDR": "Copa del Rey", "DFB": "DFB-Pokal", "CIT": "Coppa Italia",
}
MIN_SEASON = 2012  # the file's first full season (2012/13)

# Which appearances to keep:
#  - the 5 domestic leagues
#  - Champions League, Europa League and domestic cups (not qualifying rounds, not national-team tournaments)
#  - only for players who also played in one of the 5 leagues that season
QUERY = f"""
WITH games_n AS (
    -- the file stores season as text ('2023'); make it a number so it can be compared
    SELECT * EXCLUDE (season), CAST(season AS INTEGER) AS season FROM games
),
league_pairs AS (
    SELECT DISTINCT a.player_id, g.season
    FROM appearances a JOIN games_n g ON g.game_id = a.game_id
    WHERE g.competition_id IN ({",".join(repr(k) for k in LEAGUES)}) AND g.season >= {MIN_SEASON}
)
SELECT
    a.player_id,
    any_value(a.player_name)                                   AS player_name,
    any_value(p.position)                                      AS position,
    g.season,
    g.competition_id,
    any_value(c.name)                                          AS competition_slug,
    any_value(c.type)                                          AS competition_kind,
    CASE WHEN a.player_club_id = g.home_club_id THEN g.home_club_name ELSE g.away_club_name END AS club,
    count(*)                                                   AS games,
    sum(coalesce(a.minutes_played, 0))                         AS minutes,
    sum(coalesce(a.goals, 0))                                  AS goals,
    sum(coalesce(a.assists, 0))                                AS assists,
    sum(coalesce(a.yellow_cards, 0))                           AS yellow_cards,
    sum(coalesce(a.red_cards, 0))                              AS red_cards,
    CASE WHEN any_value(p.position) = 'Goalkeeper' THEN
        sum(CASE WHEN a.minutes_played >= 90
                  AND ((a.player_club_id = g.home_club_id AND g.away_club_goals = 0)
                    OR (a.player_club_id = g.away_club_id AND g.home_club_goals = 0))
                 THEN 1 ELSE 0 END)
    END                                                        AS clean_sheets
FROM appearances a
JOIN games_n g ON g.game_id = a.game_id
JOIN league_pairs lp ON lp.player_id = a.player_id AND lp.season = g.season
LEFT JOIN players p ON p.player_id = a.player_id
LEFT JOIN competitions c ON c.competition_id = g.competition_id
WHERE g.season >= {MIN_SEASON}
  AND (
        g.competition_id IN ({",".join(repr(k) for k in LEAGUES)})
        OR (
            (c.type IN ('domestic_cup', 'international_cup') OR g.competition_id = 'EL')
            AND g.competition_id NOT IN ('NLP', 'GRP', 'RUP', 'SFA', 'DKP', 'UKRP')  -- other countries' cups
            AND lower(c.name) NOT LIKE '%qualif%'
            AND lower(c.name) NOT LIKE '%world-cup%'
            AND lower(c.name) NOT LIKE '%european-championship%'
            AND lower(c.name) NOT LIKE '%nations-league%'
            AND lower(c.name) NOT LIKE '%copa-america%'
            AND lower(c.name) NOT LIKE '%africa%'
            AND lower(c.name) NOT LIKE '%asian%'
            AND lower(c.name) NOT LIKE '%gold-cup%'
        )
      )
GROUP BY a.player_id, g.season, g.competition_id, club
"""

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS player_season_stats (
    player_id        INTEGER NOT NULL,
    player_name      TEXT    NOT NULL,
    position         TEXT,
    season           TEXT    NOT NULL,   -- same format as the standings: 2324 means 2023/24
    competition_id   TEXT    NOT NULL,
    competition      TEXT    NOT NULL,
    competition_type TEXT    NOT NULL,   -- league, europe or cup
    club             TEXT    NOT NULL,
    games            INTEGER NOT NULL,
    minutes          INTEGER NOT NULL,
    goals            INTEGER NOT NULL,
    assists          INTEGER NOT NULL,
    yellow_cards     INTEGER NOT NULL,
    red_cards        INTEGER NOT NULL,
    clean_sheets     INTEGER,            -- goalkeepers only
    PRIMARY KEY (player_id, season, competition_id, club)
);
CREATE INDEX IF NOT EXISTS idx_pss_leaders ON player_season_stats (competition_id, season, goals DESC);
CREATE INDEX IF NOT EXISTS idx_pss_player ON player_season_stats (player_id);
"""

INSERT_SQL = """
INSERT INTO player_season_stats
    (player_id, player_name, position, season, competition_id, competition, competition_type, club,
     games, minutes, goals, assists, yellow_cards, red_cards, clean_sheets)
VALUES %s
"""


def season_code(start_year):
    """2023 -> '2324', the same format the standings use."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def competition_name(comp_id, slug):
    if comp_id in NICE_NAMES:
        return NICE_NAMES[comp_id]
    return (slug or comp_id).replace("-", " ").title()


def competition_type(comp_id, kind):
    if comp_id in LEAGUES:
        return "league"
    if kind == "international_cup" or comp_id in ("CL", "EL"):
        return "europe"
    return "cup"


def build_rows(duckdb_path):
    con = duckdb.connect(duckdb_path, read_only=True)
    raw = con.execute(QUERY).fetchall()
    rows = []
    for (player_id, name, position, season, comp_id, slug, kind, club, games, minutes,
         goals, assists, yellow, red, clean_sheets) in raw:
        if not name or not club:
            continue
        rows.append((
            int(player_id), name, position, season_code(int(season)), comp_id,
            competition_name(comp_id, slug), competition_type(comp_id, kind), club,
            int(games), int(minutes), int(goals), int(assists), int(yellow), int(red),
            None if clean_sheets is None else int(clean_sheets),
        ))
    return rows


def summarise(rows):
    print(f"\nRows built: {len(rows):,}")

    print("\nCompetitions included (rows | name | type):")
    counts = Counter((r[4], r[5], r[6]) for r in rows)
    for (comp_id, name, kind), n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>7,} | {comp_id:<5} {name} | {kind}")

    print("\nRows per season:")
    per_season = Counter(r[3] for r in rows)
    print("  " + "  ".join(f"{s}:{n}" for s, n in sorted(per_season.items())))

    # check against numbers you can verify: Premier League 2023/24 (code 2324)
    goals = defaultdict(lambda: [0, 0])
    keepers = defaultdict(int)
    for r in rows:
        if r[3] == "2324" and r[4] == "GB1":
            goals[r[1]][0] += r[10]
            goals[r[1]][1] += r[11]
            if r[14]:
                keepers[r[1]] += r[14]
    print("\nCheck, Premier League 2023/24 top scorers (Haaland should have 27):")
    for name, (g, a) in sorted(goals.items(), key=lambda kv: -kv[1][0])[:5]:
        print(f"  {name}: {g} goals, {a} assists")
    print("Check, goalkeepers with most clean sheets (Raya should have 16):")
    for name, cs in sorted(keepers.items(), key=lambda kv: -kv[1])[:3]:
        print(f"  {name}: {cs}")


def find_database_url():
    for name in ("DATABASE_URL", "DATABASE_URL_POOLED"):
        value = os.environ.get(name)
        if not value:
            for env_file in ("api.env", ".env"):
                path = pathlib.Path(env_file)
                if not path.exists():
                    continue
                for line in path.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("export "):
                        line = line[len("export "):].strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    if key.strip() == name:
                        value = val.strip().strip('"').strip("'")
        if value:
            return name, value
    return None, None


def load(rows):
    from psycopg2.extras import execute_values
    import psycopg2

    name, url = find_database_url()
    if not url:
        raise SystemExit("No DATABASE_URL (or DATABASE_URL_POOLED) found in api.env.")
    print(f"\nConnecting with {name} (value not shown)...")
    conn = psycopg2.connect(url)
    try:
        with conn, conn.cursor() as cur:   # one transaction: all or nothing
            cur.execute(CREATE_SQL)
            cur.execute("DELETE FROM player_season_stats")
            execute_values(cur, INSERT_SQL, rows, page_size=2000)
            cur.execute("SELECT count(*) FROM player_season_stats")
            print(f"Loaded. player_season_stats now has {cur.fetchone()[0]:,} rows.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duckdb", default="data/transfermarkt-datasets.duckdb")
    parser.add_argument("--load", action="store_true", help="write the table to the database")
    args = parser.parse_args()

    if not pathlib.Path(args.duckdb).exists():
        raise SystemExit(f"Cannot find {args.duckdb}. Pass the right path with --duckdb.")

    rows = build_rows(args.duckdb)
    summarise(rows)

    if args.load:
        load(rows)
    else:
        print("\nNothing was written to your database. If the numbers above look right, run again with --load.")


if __name__ == "__main__":
    sys.exit(main())
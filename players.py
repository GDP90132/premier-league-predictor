"""Player stats endpoints. They read the player_season_stats table
(built by build_player_stats.py) and are added to the app from main.py.
"""
from fastapi import APIRouter, HTTPException, Query

from db import query_df

router = APIRouter()

# stat name -> (column to total, sort order). Only these names are ever put into the SQL.
STATS = {
    "goals": ("goals", "goals DESC, assists DESC, games ASC"),
    "assists": ("assists", "assists DESC, goals DESC, games ASC"),
    "clean_sheets": ("clean_sheets", "clean_sheets DESC, games ASC"),
    "minutes": ("minutes", "minutes DESC"),
    "games": ("games", "games DESC, minutes DESC"),
}

TYPE_ORDER = "CASE competition_type WHEN 'league' THEN 0 WHEN 'europe' THEN 1 ELSE 2 END"


def records(df, whole_number_columns=()):
    """DataFrame -> list of dicts. NaN becomes None and whole numbers stay whole (16, not 16.0)."""
    for col in whole_number_columns:
        if col in df:
            df[col] = df[col].astype("Int64")
    return df.astype(object).where(df.notna(), None).to_dict("records")


COUNT_COLUMNS = ("games", "minutes", "goals", "assists", "yellow_cards", "red_cards", "clean_sheets")


@router.get("/player-seasons")
def player_seasons():
    """Seasons that have player stats, newest first. Same format as /seasons (2324 means 2023/24)."""
    df = query_df("SELECT DISTINCT season FROM player_season_stats ORDER BY season DESC", (), pooled=True)
    return {"seasons": df["season"].tolist()}


@router.get("/player-competitions")
def player_competitions():
    """Competitions with player stats, for a dropdown: leagues first, then Europe, then cups."""
    df = query_df(
        f"""SELECT competition_id AS id, competition AS name, competition_type AS type
            FROM player_season_stats
            GROUP BY competition_id, competition, competition_type
            ORDER BY {TYPE_ORDER}, count(*) DESC""",
        (), pooled=True)
    return {"competitions": records(df)}


@router.get("/top-players")
def top_players(
    stat: str = "goals",
    competition: str = "all",
    season: str = "all",
    limit: int = Query(20, ge=1, le=100),
):
    """Leaders for one stat. competition is an id from /player-competitions or 'all'.
    season is a code from /player-seasons or 'all' (every season since 2012/13)."""
    if stat not in STATS:
        raise HTTPException(status_code=400, detail=f"Unknown stat '{stat}'. Choose from {list(STATS)}")
    column, order = STATS[stat]

    where, params = [], []
    if competition != "all":
        where.append("competition_id = %s")
        params.append(competition)
    if season != "all":
        where.append("season = %s")
        params.append(season)
    if stat == "clean_sheets":
        where.append("position = 'Goalkeeper'")
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
        SELECT player_id,
               max(player_name)                                AS player_name,
               max(position)                                   AS position,
               string_agg(DISTINCT club, ', ' ORDER BY club)   AS clubs,
               sum(games)                                      AS games,
               sum(minutes)                                    AS minutes,
               sum(goals)                                      AS goals,
               sum(assists)                                    AS assists,
               sum(clean_sheets)                               AS clean_sheets
        FROM player_season_stats
        {clause}
        GROUP BY player_id
        HAVING sum({column}) > 0
        ORDER BY {order}, player_name
        LIMIT %s
    """
    df = query_df(sql, tuple(params + [limit]), pooled=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return {
        "stat": stat,
        "competition": competition,
        "season": season,
        "players": records(df, COUNT_COLUMNS),
    }


@router.get("/player-search")
def player_search(q: str = Query(..., min_length=2, max_length=60)):
    """Find players by name (part of a name works). Accents must match, so 'Ødegaard' not 'Odegaard'."""
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    df = query_df(
        """SELECT player_id,
                  max(player_name) AS player_name,
                  max(position)    AS position,
                  min(season)      AS first_season,
                  max(season)      AS last_season,
                  sum(goals)       AS goals,
                  sum(assists)     AS assists
           FROM player_season_stats
           WHERE player_name ILIKE %s
           GROUP BY player_id
           ORDER BY sum(games) DESC, max(player_name)
           LIMIT 20""",
        ("%" + escaped + "%",), pooled=True)
    return {"query": q, "players": records(df, COUNT_COLUMNS)}


@router.get("/player/{player_id}")
def player(player_id: int):
    """One player's rows: every season, split by competition and club."""
    df = query_df(
        f"""SELECT player_name, position, season, competition_id, competition, competition_type, club,
                   games, minutes, goals, assists, yellow_cards, red_cards, clean_sheets
            FROM player_season_stats
            WHERE player_id = %s
            ORDER BY season DESC, {TYPE_ORDER}, competition""",
        (player_id,), pooled=True)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No stats for player {player_id}")
    info = {"player_id": player_id, "name": df["player_name"].iloc[0], "position": df["position"].iloc[0]}
    rows = records(df.drop(columns=["player_name", "position"]), COUNT_COLUMNS)
    return {"player": info, "rows": rows}
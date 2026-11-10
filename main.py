"""FastAPI layer over the football database and the prediction model.

Run it from the project folder (so api.env is found):
    uvicorn main:app --reload
Then open http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from db import get_current_teams, get_recent_matches, query_df
from predict import predict_match

LEAGUES = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]

app = FastAPI(title="Football Predictor API")

# Lets a web page on another address (your JS frontend) call this API.
# "*" is fine while building. Before deploying, replace it with your frontend's URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://football-match-predictor.netlify.app","http://127.0.0.1:5500",
        "http://localhost:5500", ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def records(df):
    """DataFrame -> list of dicts, with NaN turned into None so it is valid JSON."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


def check_league(league: str) -> None:
    if league not in LEAGUES:
        raise HTTPException(
            status_code=404, detail=f"Unknown league '{league}'. Choose from {LEAGUES}")


# ---------- basics ----------

@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/leagues")
def leagues():
    return LEAGUES


@app.get("/teams")
def teams(league: str):
    check_league(league)
    return {"league": league, "teams": get_current_teams(league)}


@app.get("/recent-matches")
def recent_matches(team: str, n: int = Query(5, ge=1, le=20)):
    df = get_recent_matches(team, n)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No matches found for '{team}'")
    return records(df)


# ---------- prediction ----------

@app.get("/predict")
def predict(home: str, away: str):
    if home == away:
        raise HTTPException(status_code=400, detail="Pick two different teams")
    try:
        return predict_match(home, away)
    except ValueError as e:  # not enough history, no recent matches, missing stats
        raise HTTPException(status_code=400, detail=str(e))


# ---------- standings and stats (computed from the matches table) ----------

@app.get("/seasons")
def seasons(league: str):
    check_league(league)
    df = query_df(
        "SELECT DISTINCT season FROM matches WHERE league = %s ORDER BY season DESC",
        (league,), pooled=True)
    return {"league": league, "seasons": df["season"].tolist()}


STANDINGS_SQL = """
    WITH t AS (
        SELECT home_team AS team, home_goals AS gf, away_goals AS ga
        FROM matches
        WHERE league = %s AND season = %s
          AND home_goals IS NOT NULL AND away_goals IS NOT NULL
        UNION ALL
        SELECT away_team, away_goals, home_goals
        FROM matches
        WHERE league = %s AND season = %s
          AND home_goals IS NOT NULL AND away_goals IS NOT NULL
    )
    SELECT team,
           count(*)                                   AS played,
           count(*) FILTER (WHERE gf > ga)            AS won,
           count(*) FILTER (WHERE gf = ga)            AS drawn,
           count(*) FILTER (WHERE gf < ga)            AS lost,
           sum(gf)                                    AS gf,
           sum(ga)                                    AS ga,
           sum(gf - ga)                               AS gd,
           sum(CASE WHEN gf > ga THEN 3 WHEN gf = ga THEN 1 ELSE 0 END) AS points
    FROM t
    GROUP BY team
    ORDER BY points DESC, gd DESC, gf DESC, team
"""


@app.get("/standings")
def standings(league: str, season: str):
    check_league(league)
    df = query_df(STANDINGS_SQL, (league, season, league, season), pooled=True)
    if df.empty:
        raise HTTPException(
            status_code=404, detail=f"No matches for {league} in season '{season}'")
    df.insert(0, "position", range(1, len(df) + 1))
    return {"league": league, "season": season, "table": records(df)}


CLEAN_SHEETS_SQL = """
    WITH t AS (
        SELECT home_team AS team, away_goals AS conceded
        FROM matches
        WHERE league = %s AND season = %s
          AND home_goals IS NOT NULL AND away_goals IS NOT NULL
        UNION ALL
        SELECT away_team, home_goals
        FROM matches
        WHERE league = %s AND season = %s
          AND home_goals IS NOT NULL AND away_goals IS NOT NULL
    )
    SELECT team,
           count(*) FILTER (WHERE conceded = 0) AS clean_sheets,
           count(*)                             AS played
    FROM t
    GROUP BY team
    ORDER BY clean_sheets DESC, team
    LIMIT %s
"""


@app.get("/clean-sheets")
def clean_sheets(league: str, season: str, limit: int = Query(10, ge=1, le=30)):
    check_league(league)
    df = query_df(CLEAN_SHEETS_SQL, (league, season, league, season, limit), pooled=True)
    if df.empty:
        raise HTTPException(
            status_code=404, detail=f"No matches for {league} in season '{season}'")
    return {"league": league, "season": season, "teams": records(df)}
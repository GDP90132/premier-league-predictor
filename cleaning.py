import pandas as pd

from db import MATCH_COLS

RENAME = {
    "Div": "div", "Date": "match_date", "HomeTeam": "home_team", "AwayTeam": "away_team",
    "FTHG": "home_goals", "FTAG": "away_goals", "FTR": "result",
    "HTHG": "ht_home_goals", "HTAG": "ht_away_goals", "HTR": "ht_result",
    "HS": "home_shots", "AS": "away_shots", "HST": "home_sot", "AST": "away_sot",
    "HC": "home_corners", "AC": "away_corners", "HF": "home_fouls", "AF": "away_fouls",
    "HY": "home_yellows", "AY": "away_yellows", "HR": "home_reds", "AR": "away_reds",
    "B365H": "b365_home", "B365D": "b365_draw", "B365A": "b365_away",
}


def clean_matches(raw: pd.DataFrame, league: str, season: str) -> pd.DataFrame:
    """Raw football-data.co.uk rows -> rows ready for the matches table."""
    # only finished matches: key fields and the final score must exist
    df = raw.dropna(subset=["Date", "HomeTeam",
                    "AwayTeam", "FTHG", "FTAG", "FTR"]).copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed")
    df["match_id"] = (
        df["Div"] + "_" + df["Date"].dt.strftime("%Y-%m-%d")
        + "_" + df["HomeTeam"] + "_" + df["AwayTeam"]
    )
    df["league"] = league
    df["season"] = season
    df = df.rename(columns=RENAME)
    for col in MATCH_COLS:  # a column the file lacks becomes empty
        if col not in df.columns:
            df[col] = None
    return df[MATCH_COLS]

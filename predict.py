from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson

from db import query_df

MODELS_DIR = Path(__file__).resolve().parent / "models"
GOAL_LINES = [1.5, 2.5, 3.5]
CORNER_LINES = [8.5, 9.5, 10.5, 11.5]
MAX_GAP_DAYS = 150  # same rule as features.py: ignore history after a long gap
_cache = {}


def _load(name: str) -> dict:
    if name not in _cache:
        _cache[name] = joblib.load(MODELS_DIR / f"{name}.joblib")
    return _cache[name]


def _ref_date(as_of):
    return pd.Timestamp(as_of).date() if as_of else date.today()


def team_form(team: str, as_of=None) -> dict:
    """Last-5 averages for a team, using only matches BEFORE `as_of` (default: today)."""
    ref = _ref_date(as_of)
    sql = """
        SELECT match_date, home_team, home_goals, away_goals, home_shots, away_shots,
               home_sot, away_sot, home_corners, away_corners
        FROM matches
        WHERE (home_team = %s OR away_team = %s) AND match_date < %s
        ORDER BY match_date DESC
        LIMIT 5
    """
    df = query_df(sql, (team, team, ref), pooled=True)
    if len(df) < 5:
        raise ValueError(f"not enough match history for '{team}'")
    for c in df.columns.drop(["match_date", "home_team"]):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    is_home = df["home_team"] == team
    def pick(h, a): return df[h].where(
        is_home, df[a])  # my value, home or away
    gf, ga = pick("home_goals", "away_goals"), pick("away_goals", "home_goals")
    rest = (ref - df["match_date"].iloc[0]).days
    if rest > MAX_GAP_DAYS:
        raise ValueError(
            f"'{team}' has no recent matches (last one {rest} days ago)")

    form = {
        "pts5": float((3 * (gf > ga) + (gf == ga)).mean()),
        "gf5": float(gf.mean()),
        "ga5": float(ga.mean()),
        "shots5": float(pick("home_shots", "away_shots").mean()),
        "sot5": float(pick("home_sot", "away_sot").mean()),
        "cf5": float(pick("home_corners", "away_corners").mean()),
        "ca5": float(pick("away_corners", "home_corners").mean()),
        "rest_days": float(rest),
    }
    if any(pd.isna(v) for v in form.values()):
        raise ValueError(f"missing stats in the last 5 matches of '{team}'")
    return form


def head_to_head(home: str, away: str, as_of=None) -> dict:
    """Average total goals and corners in the last (up to) 5 meetings, either venue."""
    ref = _ref_date(as_of)
    sql = """
        SELECT home_goals + away_goals AS tg, home_corners + away_corners AS tc
        FROM matches
        WHERE ((home_team = %s AND away_team = %s) OR (home_team = %s AND away_team = %s))
          AND match_date < %s
        ORDER BY match_date DESC
        LIMIT 5
    """
    df = query_df(sql, (home, away, away, home, ref), pooled=True)
    df = df.apply(pd.to_numeric, errors="coerce")
    return {
        "h2h_goals5": float(df["tg"].mean()) if len(df) else np.nan,
        "h2h_corners5": float(df["tc"].mean()) if len(df) else np.nan,
        "h2h_n": float(len(df)),
    }


def build_features(home: str, away: str, as_of=None) -> dict:
    h, a = team_form(home, as_of), team_form(away, as_of)
    feats = {f"home_{k}": v for k, v in h.items()}
    feats.update({f"away_{k}": v for k, v in a.items()})
    for c in ["pts5", "gf5", "ga5", "shots5", "sot5"]:
        feats[f"{c}_diff"] = h[c] - a[c]
    feats["form_total_goals"] = (
        h["gf5"] + a["ga5"]) / 2 + (a["gf5"] + h["ga5"]) / 2
    feats["form_total_corners"] = (
        h["cf5"] + a["ca5"]) / 2 + (a["cf5"] + h["ca5"]) / 2
    feats.update(head_to_head(home, away, as_of))
    return feats


def _row(feats: dict, saved: dict) -> pd.DataFrame:
    # columns in the order the model was trained on
    return pd.DataFrame([feats])[saved["features"]]


def predict_outcome(home: str, away: str, as_of=None, model_name="logistic_regression") -> dict:
    saved = _load(model_name)
    model = saved["model"]
    probs = model.predict_proba(
        _row(build_features(home, away, as_of), saved))[0]
    # the model reports its own class order
    by_class = dict(zip(model.classes_, probs))
    return {
        "home_win": round(float(by_class["H"]) * 100, 1),
        "draw": round(float(by_class["D"]) * 100, 1),
        "away_win": round(float(by_class["A"]) * 100, 1),
    }


def predict_totals(home: str, away: str, as_of=None) -> dict:
    feats = build_features(home, away, as_of)
    out = {}
    for kind, lines in (("goals", GOAL_LINES), ("corners", CORNER_LINES)):
        saved = _load(f"{kind}_poisson_regression")
        expected = float(saved["model"].predict(_row(feats, saved))[0])
        out[kind] = {
            "expected": round(expected, 2),
            "over": {str(line): round(float(poisson.sf(np.floor(line), expected)) * 100, 1)
                     for line in lines},
        }
    return out


def predict_match(home: str, away: str, as_of=None) -> dict:
    return {"home": home, "away": away,
            "outcome": predict_outcome(home, away, as_of),
            "totals": predict_totals(home, away, as_of)}


if __name__ == "__main__":
    print(predict_match("Arsenal", "Chelsea"))
    print("\nleakage check, Newcastle as of 2026-11-02 (pts5 should be 1.2):")
    print(team_form("Newcastle", as_of="2026-11-02"))

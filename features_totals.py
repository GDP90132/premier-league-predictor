import numpy as np
import pandas as pd

df = pd.read_csv("data/matches_clean.csv", parse_dates=["Date"])
df = df.sort_values(["Date", "match_id"]).reset_index(drop=True)


# 1. one row per team per match (goals, shots, corners for and against)
def side(team_col, venue, gf, ga, shots, sot, c_for, c_against):
    return pd.DataFrame({
        "match_id": df["match_id"], "Date": df["Date"], "team": df[team_col],
        "venue": venue, "gf": df[gf], "ga": df[ga],
        "shots": df[shots], "sot": df[sot],
        "cf": df[c_for], "ca": df[c_against],
    })


home = side("HomeTeam", "home", "FTHG", "FTAG", "HS", "HST", "HC", "AC")
away = side("AwayTeam", "away", "FTAG", "FTHG", "AS", "AST", "AC", "HC")
long = pd.concat([home, away]).sort_values(
    ["team", "Date"]).reset_index(drop=True)

# 2. rest days and last-5 averages, shifted so a match never sees itself
long["rest_days"] = long.groupby("team")["Date"].diff().dt.days
stats = ["gf", "ga", "shots", "sot", "cf", "ca"]
for c in stats:
    long[f"{c}5"] = long.groupby("team")[c].transform(
        lambda s: s.shift(1).rolling(5, min_periods=5).mean()
    )
feat = [f"{c}5" for c in stats]
long.loc[long["rest_days"] > 150, feat] = None  # promotion/relegation gaps

# 3. back to one row per match
cols = feat + ["rest_days"]
home_f = long[long["venue"] == "home"].set_index(
    "match_id")[cols].add_prefix("home_")
away_f = long[long["venue"] == "away"].set_index(
    "match_id")[cols].add_prefix("away_")
out = df.set_index("match_id").join(home_f).join(away_f)

# 4. matchup features: my attack vs their defence, and the reverse
out["form_total_goals"] = (
    (out["home_gf5"] + out["away_ga5"]) / 2 +
    (out["away_gf5"] + out["home_ga5"]) / 2
)
out["form_total_corners"] = (
    (out["home_cf5"] + out["away_ca5"]) / 2 +
    (out["away_cf5"] + out["home_ca5"]) / 2
)

# 5. head-to-head: average total goals/corners in the last 5 meetings (before this one)
first = np.where(df["HomeTeam"] < df["AwayTeam"],
                 df["HomeTeam"], df["AwayTeam"])
second = np.where(df["HomeTeam"] < df["AwayTeam"],
                  df["AwayTeam"], df["HomeTeam"])
df["pair"] = df["Div"] + "|" + \
    pd.Series(first, index=df.index) + "|" + pd.Series(second, index=df.index)
df["tg"] = df["FTHG"] + df["FTAG"]
df["tc"] = df["HC"] + df["AC"]
g = df.groupby("pair")
df["h2h_goals5"] = g["tg"].transform(
    lambda s: s.shift(1).rolling(5, min_periods=1).mean())
df["h2h_corners5"] = g["tc"].transform(
    lambda s: s.shift(1).rolling(5, min_periods=1).mean())
# how many previous meetings exist (max 5)
df["h2h_n"] = g.cumcount().clip(upper=5)
out = out.join(df.set_index("match_id")[
               ["h2h_goals5", "h2h_corners5", "h2h_n"]])

# 6. drop rows with no team history (h2h may stay empty, the models handle that)
need = [c for c in out.columns if c.startswith(("home_", "away_"))]
need += ["form_total_goals", "form_total_corners"]
out = out.dropna(subset=need).reset_index()
out.to_csv("data/features_totals.csv", index=False)

print(out.shape)
print("avg total goals:  ", round((out["FTHG"] + out["FTAG"]).mean(), 2))
print("avg total corners:", round((out["HC"] + out["AC"]).mean(), 2))
print(out[["Date", "HomeTeam", "AwayTeam",
      "form_total_goals", "h2h_goals5", "h2h_n"]].tail())

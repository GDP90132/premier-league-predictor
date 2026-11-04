import pandas as pd

from db import get_matches_for_features

df = get_matches_for_features()
df = df.sort_values(["Date", "match_id"]).reset_index(drop=True)
# 1. one row per team per match


def side(prefix_team, venue, gf, ga, shots, sot):
    return pd.DataFrame({
        "match_id": df["match_id"], "Date": df["Date"], "team": df[prefix_team],
        "venue": venue, "gf": df[gf], "ga": df[ga],
        "shots": df[shots], "sot": df[sot],
    })


home = side("HomeTeam", "home", "FTHG", "FTAG", "HS", "HST")
away = side("AwayTeam", "away", "FTAG", "FTHG", "AS", "AST")
long = pd.concat([home, away]).sort_values(
    ["team", "Date"]).reset_index(drop=True)

# points earned in each match
long["pts"] = (long["gf"] > long["ga"]) * 3 + (long["gf"] == long["ga"]) * 1

# 2. days since this team's previous match
long["rest_days"] = long.groupby("team")["Date"].diff().dt.days

# 3. last-5 averages that only use PREVIOUS matches (shift(1))
for col in ["pts", "gf", "ga", "shots", "sot"]:
    long[f"{col}5"] = long.groupby("team")[col].transform(
        lambda s: s.shift(1).rolling(5, min_periods=5).mean()
    )

# 4. blank out history if the gap is too long (promotion/relegation)
stats = ["pts5", "gf5", "ga5", "shots5", "sot5"]
long.loc[long["rest_days"] > 150, stats] = None

# 5. put home and away features back on one row per match
feat_cols = stats + ["rest_days"]
home_f = long[long["venue"] == "home"].set_index(
    "match_id")[feat_cols].add_prefix("home_")
away_f = long[long["venue"] == "away"].set_index(
    "match_id")[feat_cols].add_prefix("away_")
out = df.set_index("match_id").join(home_f).join(away_f).reset_index()

for c in stats:
    out[f"{c}_diff"] = out[f"home_{c}"] - out[f"away_{c}"]

out = out.dropna(
    subset=[c for c in out.columns if c.startswith(("home_", "away_"))])
out.to_csv("data/features.csv", index=False)

print(out.shape)
print(out["FTR"].value_counts(normalize=True))
print(out[["Date", "HomeTeam", "AwayTeam", "home_pts5", "away_pts5", "FTR"]].tail())

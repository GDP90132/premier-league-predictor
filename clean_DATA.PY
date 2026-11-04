import pandas as pd

df = pd.read_csv("data/all_matches_raw.csv",
                 low_memory=False, dtype={"season": str})

# 1. drop the 8 empty rows
df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam"])

# 2. turn text dates into real dates (day first)
df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed")

# 3. build a unique id for each match
df["match_id"] = (
    df["Div"] + "_" + df["Date"].dt.strftime("%Y-%m-%d")
    + "_" + df["HomeTeam"] + "_" + df["AwayTeam"]
)
print("duplicate ids:", df["match_id"].duplicated().sum())

# 4. keep only the columns we need
wanted = [
    "match_id", "Div", "league", "season", "Date", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
    "HS", "AS", "HST", "AST", "HC", "AC", "HF", "AF", "HY", "AY", "HR", "AR",
    "B365H", "B365D", "B365A",
]
df = df[[c for c in wanted if c in df.columns]].sort_values("Date")

df.to_csv("data/matches_clean.csv", index=False)
print(df.shape)
print(df.isna().sum())

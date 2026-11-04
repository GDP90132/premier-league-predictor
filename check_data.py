import pandas as pd

df = pd.read_csv("data/all_matches_raw.csv", low_memory=False)

# 1. blank rows in the key columns
print(df[["Date", "HomeTeam", "AwayTeam", "FTR"]].isna().sum())

# 2. dates: day first, mixed formats allowed
df["Date"] = pd.to_datetime(
    df["Date"], dayfirst=True, format="mixed", errors="coerce")
print("unparsed dates:", df["Date"].isna().sum())
print(df["Date"].min(), df["Date"].max())

# 3. which useful columns are filled, by season
cols = ["HS", "HST", "HC", "HY", "B365H", "AvgH"]
print(df.groupby("season")[cols].count())

# 4. number of distinct team names per league
print(df.groupby("league")["HomeTeam"].nunique())


df = pd.read_csv("data/all_matches_raw.csv",
                 low_memory=False, dtype={"season": str})

# the rows with missing key info
bad = df[df["Date"].isna() | df["HomeTeam"].isna()]
print(bad[["league", "season", "Div", "Date", "HomeTeam"]])

# every team name per league, alphabetical
clean = df.dropna(subset=["HomeTeam"])
for league, group in clean.groupby("league"):
    print(league, sorted(group["HomeTeam"].unique()), "\n")

import sqlite3
import pandas as pd


csv_file = "/Users/gill/premierlague_project/premier_league_complete_stats_until35thGameDayOnSeason2025-26.csv"
print("Reading kaggle player stats")
df = pd.read_csv(csv_file, encoding="utf-8")
df.columns = df.columns.str.strip()
conn = sqlite3.connect("premier_league.db")
df.to_sql("player_stats", conn, if_exists="replace", index=False)
conn.close()
print(
    "Successfully imported Kaggle player stats into 'player_stats' table inside premier_league.db!"
)
conn = sqlite3.connect("premier_league.db")
with open("get_player_stats.sql", 'r') as File:
    query = File.read()
df = pd.read_sql_query(query, conn)
conn.close()
print(df.head())


def get_top_players_goals():
    conn = sqlite3.connect("premier_league.db")
    with open("get_top_goals_scorers.sql", 'r') as file:
        query = file.read()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_top_players_assists():
    conn = sqlite3.connect("premier_league.db")
    with open("get_top_assisters.sql", 'r') as file:
        query = file.read()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_team_roster(team_name):
    conn = sqlite3.connect("premier_league.db")
    query = f"SELECT team_name, player_name,position,goals,assists,appearances FROM player_stats WHERE team_name = '{team_name}';"
    df = pd.read_sql_query(query, conn)
    conn.close()
    if df.empty:
        raise ValueError(f"no match history found for team {team_name}")
    return df


user = input("what is the name of the team: ").strip()
ask = get_team_roster(user)

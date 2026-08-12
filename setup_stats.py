import sqlite3
import pandas as pd
from pathlib import Path

# Set up dynamic paths for Streamlit Cloud and local execution
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "premier_league.db"
CSV_FILE = BASE_DIR / "premier_league_complete_stats_until35thGameDayOnSeason2025-26.csv"

# Load CSV and write to SQLite database if CSV exists
if CSV_FILE.exists():
    print("Reading player stats CSV...")
    df = pd.read_csv(CSV_FILE, encoding="utf-8")
    df.columns = df.columns.str.strip()
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("player_stats", conn, if_exists="replace", index=False)
    conn.close()
    print("Successfully imported player stats into 'player_stats' table inside premier_league.db!")


def get_top_players_goals():
    conn = sqlite3.connect(DB_PATH)
    sql_path = BASE_DIR / "get_top_goals_scorers.sql"
    with open(sql_path, 'r') as file:
        query = file.read()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_top_players_assists():
    conn = sqlite3.connect(DB_PATH)
    sql_path = BASE_DIR / "get_top_assisters.sql"
    with open(sql_path, 'r') as file:
        query = file.read()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_team_roster(team_name):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT team_name, player_name, position, goals, assists, appearances FROM player_stats WHERE team_name = ?;"
    df = pd.read_sql_query(query, conn, params=(team_name,))
    conn.close()
    if df.empty:
        raise ValueError(f"No match history found for team {team_name}")
    return df


def get_player_stats(player_name):
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT player_name, team_name, position, goals, assists, appearances 
        FROM player_stats 
        WHERE player_name LIKE ?;
    """
    df = pd.read_sql_query(query, conn, params=(f"%{player_name}%",))
    conn.close()

    if df.empty:
        raise ValueError(f"No player found matching '{player_name}'.")
    return df


def get_all_player_names():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT DISTINCT player_name FROM player_stats WHERE player_name IS NOT NULL ORDER BY player_name;"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df["player_name"].tolist()


if __name__ == "__main__":
    user = input("what is the name of the team: ").strip()
    ask = get_team_roster(user)
    print(ask)

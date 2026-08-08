import sqlite3
import joblib
import pandas as pd

# Load the trained model we saved earlier
model = joblib.load("prem_model.joblib")


def get_latest_stats(team_name, is_home=True):
    # We will build this together step-by-step
    conn = sqlite3.connect("premier_league.db")
    if is_home:
        query = f"""
            SELECT 
                Home_Team_AvgGoals AS AvgGoals,
                Home_Team_AvgConceded AS AvgConceded,
                Home_Team_Form AS Form
            FROM matches_features
            WHERE home_name = '{team_name}'
            ORDER BY utcDate DESC
            LIMIT 1
        """
    else:
        query = f"""
            SELECT 
                Away_Team_AvgGoals AS AvgGoals,
                Away_Team_AvgConceded AS AvgConceded,
                Away_Team_Form AS Form
            FROM matches_features
            WHERE away_name = '{team_name}'
            ORDER BY utcDate DESC
            LIMIT 1
        """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        raise ValueError(f"no match history found for team {team_name}")
    return df.iloc[0]


def predict_match_outcome(home_team, away_team):
    # We will build this together step-by-step
    home_stats = get_latest_stats(home_team, is_home=True)
    away_stats = get_latest_stats(away_team, is_home=False)

    goal_attack_diff = home_stats["AvgGoals"] - away_stats["AvgGoals"]
    goals_conceded_diff = home_stats["AvgConceded"] - away_stats["AvgConceded"]
    form_diff = home_stats["Form"] - away_stats["Form"]

    features_row = pd.DataFrame(
        [{
            "Home_Team_AvgGoals": home_stats["AvgGoals"],
            "Away_Team_AvgGoals": away_stats["AvgGoals"],
            "Home_Team_AvgConceded": home_stats["AvgConceded"],
            "Away_Team_AvgConceded": away_stats["AvgConceded"],
            "Home_Team_Form": home_stats["Form"],
            "Away_Team_Form": away_stats["Form"],
            "goal_attack_diff": goal_attack_diff,
            "goal_conceded_diff": goals_conceded_diff,
            "form_diff": form_diff,
        }]
    )
    probs = model.predict_proba(features_row)[0]
    return {
        "Draw": round(probs[0] * 100, 1),
        "Home Win": round(probs[1] * 100, 1),
        "Away Win": round(probs[2] * 100, 1),
    }


def get_available_teams():
    conn = sqlite3.connect("premier_league.db")
    df = pd.read_sql_query(
        "SELECT DISTINCT home_name FROM matches_features ORDER BY home_name", conn)
    conn.close()
    return df["home_name"].tolist()


if __name__ == "__main__":
    results = predict_match_outcome("Arsenal FC", "Chelsea FC")
    print(results)

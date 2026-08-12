import streamlit as st
import sqlite3
import pandas as pd

from setup_stats import (
    get_top_players_goals,
    get_top_players_assists,
    get_team_roster,
    get_player_stats,
    get_all_player_names,  # New helper function imported
)

st.set_page_config(page_title="Premier League Stats",
                   page_icon="📊", layout="wide")

st.title("📊 Premier League Statistics")
st.caption(
    "Explore top individual player metrics, search specific players, or look up team rosters.")
st.divider()

view_mode = st.radio(
    "Select View Mode:",
    ["Player Info", "Team Info"],
    horizontal=True
)

st.markdown("<br>", unsafe_allow_html=True)

if view_mode == "Player Info":
    player_tab1, player_tab2 = st.tabs(["🥇 Leaderboards", "🔍 Search Player"])

    with player_tab1:
        st.subheader("Leaderboards")
        stat_type = st.selectbox("Select Metric:", ["Goals", "Assists"])

        try:
            if stat_type == "Goals":
                df = get_top_players_goals()
            else:
                df = get_top_players_assists()
                st.dataframe(df, width="stretch", hide_index=True)
        except Exception as e:
            st.error(f"Error fetching leaderboard: {e}")

    with player_tab2:
        st.subheader("Player Search")

        try:
            # Fetch all player names for the autocomplete dropdown
            all_players = get_all_player_names()

            # Selectbox with search auto-complete functionality
            selected_player = st.selectbox(
                "Type or select a player name:",
                options=all_players,
                index=0,
                placeholder="Start typing a name (e.g., Odegaard, Saka, Salah)..."
            )

            if selected_player:
                player_df = get_player_stats(selected_player)
                st.markdown(f"### Stats for **{selected_player}**")
                st.dataframe(player_df, use_container_width=True,
                             hide_index=True)

        except Exception as e:
            st.error(f"Error searching for player: {e}")

else:
    st.subheader("🛡️ Team Roster Lookup")

    def fetch_all_teams():
        conn = sqlite3.connect("premier_league.db")
        df_teams = pd.read_sql_query(
            "SELECT DISTINCT team_name FROM player_stats WHERE team_name IS NOT NULL ORDER BY team_name;",
            conn
        )
        conn.close()
        return df_teams["team_name"].tolist()

    try:
        team_list = fetch_all_teams()
        selected_team = st.selectbox("Select a Team:", team_list)

        if selected_team:
            roster_df = get_team_roster(selected_team)
            st.markdown(f"### Squad Roster: **{selected_team}**")
            st.dataframe(roster_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Could not load team rosters: {e}")

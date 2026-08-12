import streamlit as st
import pandas as pd
from predict_match import predict_match_outcome, get_available_teams

st.set_page_config(page_title="Match Predictor", page_icon="🔮", layout="wide")

st.title("🔮 Premier League Match Predictor")
st.caption("Select two clubs to simulate outcome probabilities using your trained machine learning model.")
st.divider()

# Fetch team names directly from your matches_features table in SQLite
try:
    teams = get_available_teams()
except Exception as e:
    st.error(f"Could not load teams from database: {e}")
    teams = []

if not teams:
    st.warning(
        "No teams found in the database table 'matches_features'. Make sure your database is populated.")
else:
    col1, col2 = st.columns(2)

    with col1:
        home_team = st.selectbox("Select Home Team 🏠", teams, index=0)

    with col2:
        # Exclude selected home team from away team selection options
        away_options = [t for t in teams if t != home_team]
        away_team = st.selectbox("Select Away Team 🚀", away_options, index=0)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Predict Match Outcome ⚽", type="primary", width="stretch"):
        try:
            with st.spinner("Calculating probabilities from database features..."):
                results = predict_match_outcome(home_team, away_team)

            st.success("Prediction Complete!")
            st.subheader(f"{home_team} vs {away_team}")

            # Display probabilities in metrics
            m1, m2, m3 = st.columns(3)
            m1.metric(f"🏠 {home_team} Win", f"{results['Home Win']}%")
            m2.metric("🤝 Draw", f"{results['Draw']}%")
            m3.metric(f"🚀 {away_team} Win", f"{results['Away Win']}%")

            # Chart representation of split probabilities
            st.divider()
            st.subheader("Probability Distribution")

            df_chart = pd.DataFrame({
                "Outcome": [f"{home_team} Win", "Draw", f"{away_team} Win"],
                "Probability (%)": [results["Home Win"], results["Draw"], results["Away Win"]]
            }).set_index("Outcome")

            st.bar_chart(df_chart)

        except ValueError as ve:
            st.error(f"Data Error: {ve}")
        except Exception as ex:
            st.error(f"An unexpected error occurred: {ex}")

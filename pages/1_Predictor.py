import os

import pandas as pd
import streamlit as st

# On Streamlit Cloud the database URLs live in st.secrets. Copy them into the
# environment so db.py finds them. Locally, db.py reads api.env instead.
try:
    for key in ("DATABASE_URL", "DATABASE_URL_POOLED"):
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass

from db import get_current_teams, get_recent_matches  # noqa: E402
from predict import predict_match  # noqa: E402

st.set_page_config(page_title="Match Predictor", page_icon="🔮", layout="wide")

st.title("🔮 Match Predictor")
st.caption(
    "Top-5 European leagues. Predictions use each team's last 5 matches, rebuilt live "
    "from the database. On 3,873 unseen matches the outcome model was right 49.3% of the time "
    "(always picking home: 43.3%, bookmaker: 53.6%)."
)
st.divider()

LEAGUES = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]


@st.cache_data(ttl=3600)
def teams_for(league: str) -> list[str]:
    return get_current_teams(league)


@st.cache_data(ttl=900)
def run_prediction(home: str, away: str) -> dict:
    return predict_match(home, away)


@st.cache_data(ttl=900)
def recent(team: str) -> pd.DataFrame:
    return get_recent_matches(team, 5)


try:
    league = st.selectbox("League", LEAGUES)
    teams = teams_for(league)
except Exception as e:
    st.error(f"Could not load teams from the database: {e}")
    teams = []

if not teams:
    st.warning("No teams found. Check the database connection.")
else:
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Select Home Team 🏠", teams, index=0)
    with col2:
        away_options = [t for t in teams if t != home_team]
        away_team = st.selectbox("Select Away Team 🚀", away_options, index=0)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Predict Match ⚽", type="primary", width="stretch"):
        try:
            with st.spinner("Building features from the latest matches..."):
                result = run_prediction(home_team, away_team)
        except ValueError as ve:
            st.warning(f"Can't predict this match: {ve}")
            st.stop()
        except Exception as ex:
            st.error(f"An unexpected error occurred: {ex}")
            st.stop()

        out, totals = result["outcome"], result["totals"]

        st.success("Prediction complete!")
        st.subheader(f"{home_team} vs {away_team}")

        m1, m2, m3 = st.columns(3)
        m1.metric(f"🏠 {home_team} Win", f"{out['home_win']}%")
        m2.metric("🤝 Draw", f"{out['draw']}%")
        m3.metric(f"🚀 {away_team} Win", f"{out['away_win']}%")

        st.bar_chart(pd.DataFrame({
            "Outcome": [f"{home_team} Win", "Draw", f"{away_team} Win"],
            "Probability (%)": [out["home_win"], out["draw"], out["away_win"]],
        }).set_index("Outcome"))

        st.divider()
        g, k = st.columns(2)
        for col, key, label in ((g, "goals", "⚽ Total goals"), (k, "corners", "🚩 Total corners")):
            col.markdown(f"**{label}**: expected {totals[key]['expected']}")
            col.dataframe(
                pd.DataFrame({
                    "line": [f"Over {line}" for line in totals[key]["over"]],
                    "chance (%)": list(totals[key]["over"].values()),
                }),
                hide_index=True,
            )

        for team in (home_team, away_team):
            with st.expander(f"{team}: last 5 matches"):
                st.dataframe(recent(team), hide_index=True)

        st.caption("A modest signal, not betting advice. The models beat naive baselines "
                   "but not the bookmakers.")

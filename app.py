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

from db import query_df  # noqa: E402

st.set_page_config(page_title="Football Match Predictor", layout="wide")


@st.cache_data(ttl=3600)
def database_summary() -> dict:
    df = query_df(
        "SELECT count(*) AS n, min(match_date) AS first, max(match_date) AS last, "
        "count(DISTINCT league) AS leagues FROM matches",
        pooled=True,
    )
    row = df.iloc[0]
    return {"matches": int(row["n"]), "first": row["first"], "last": row["last"],
            "leagues": int(row["leagues"])}


st.title("Football Match Predictor")
st.caption(
    "Match outcome, goals and corners predictions for Europe's top five leagues.")
st.divider()

# ---- live data summary ----
try:
    s = database_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matches in database", f"{s['matches']:,}")
    c2.metric("Leagues", s["leagues"])
    c3.metric("Earliest match", str(s["first"]))
    c4.metric("Latest match", str(s["last"]))
except Exception as e:
    st.info(f"Database summary is unavailable right now: {e}")

st.markdown("<br>", unsafe_allow_html=True)

# ---- about ----
left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("About")
    st.write(
        "This project predicts the result of football matches in the Premier League, "
        "La Liga, Bundesliga, Serie A and Ligue 1. Twenty years of results are stored "
        "in a PostgreSQL database that refreshes itself every few hours. For each "
        "match, the models use both teams' last five games: points, goals scored and "
        "conceded, shots, corners and days of rest."
    )
    st.write(
        "Every feature is built only from games played before the match being "
        "predicted, and models are evaluated on matches they have never seen "
        "(trained on games before July 2024, tested on 3,873 games since). That "
        "keeps the reported accuracy honest."
    )

    st.subheader("Pages")
    st.markdown(
        "- **Predictor**: pick two teams to see win, draw and loss probabilities, "
        "expected goals and corners, and the chance of going over common lines. "
        "Runs on live database data.\n"
        "- **Stats**: player leaderboards and squad rosters from a season snapshot "
        "(through gameweek 35 of 2025/26).\n"
        "- **Standing**: a Premier League table from a saved snapshot."
    )

with right:
    st.subheader("Model performance")
    st.caption("3,873 unseen matches, August 2024 to November 2026")
    st.table(pd.DataFrame({
        "Method": ["Always pick home", "This model", "Bookmaker (Bet365)"],
        "Accuracy": ["43.2%", "49.3%", "53.6%"],
        "Log loss": ["1.075", "1.018", "0.970"],
    }).set_index("Method"))
    st.write(
        "The model beats a naive baseline but does not beat bookmaker odds. "
        "Bookmakers see lineups, injuries and market information that this model "
        "does not."
    )

st.divider()

# ---- technical details ----
st.subheader("How it works")
st.markdown(
    "1. **Data**: match results and statistics for five leagues from "
    "football-data.co.uk, 2005/06 to the current season.\n"
    "2. **Storage**: PostgreSQL with a raw table of untouched rows and a cleaned "
    "table keyed on a unique match ID. A scheduled GitHub Actions job upserts new "
    "results, so reruns never create duplicates.\n"
    "3. **Features**: rolling last-five-match averages, shifted so a match never "
    "sees its own result.\n"
    "4. **Models**: logistic regression for the match outcome and Poisson "
    "regression for total goals and corners.\n"
    "5. **App**: team form is recomputed from the database at prediction time."
)

st.caption(
    "For information and portfolio purposes only. This is not betting advice. "
    "Data: football-data.co.uk."
)

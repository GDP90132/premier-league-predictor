import streamlit as st

st.set_page_config(
    page_title="Premier League Hub",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚽ Premier League Analytics & Prediction Hub")
st.caption(
    "A machine learning and SQL-powered dashboard for season stats and match predictions.")
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Data Source", value="Kaggle Datasets")
with col2:
    st.metric(label="Model Type", value="3-Way Result Classifier")
with col3:
    st.metric(label="Model Accuracy", value="~50%")

st.markdown("""
Welcome to the Premier League Analytics Hub! Use the **sidebar menu on the left** to navigate through the features:

* **🔮 Match Predictor:** Select home and away teams to see win/draw probabilities.
* **📊 Player & Team Stats:** Analyze individual leaders or explore full squad rosters.
* **🏆 Standings:** Check the current league standings, goal differences, and point totals.
""")

st.info("👈 Select a page from the sidebar to begin!")

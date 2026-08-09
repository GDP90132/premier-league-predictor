import streamlit as st

st.set_page_config(page_title="Premier League Dashboard",
                   page_icon="⚽", layout="wide", initial_sidebar_state="expanded")
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
Welcome to the dashboard! Use the **sidebar menu on the left** to navigate through the app:

* **🔮 Match Predictor (`1_Predictor`):** Select any two Premier League clubs...
* **📊 Team Info & Stats (`2_Team_Info`):** View overall league leaderboards...
""")

st.info(
    "👈 Open the sidebar on the left to start predicting matches or exploring team stats!"
)

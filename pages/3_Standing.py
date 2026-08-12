import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="League Standings", page_icon="🏆", layout="wide")

st.title("🏆 Premier League Standings")
st.caption("Current season table loaded from standings.csv")
st.divider()

CSV_FILE = "standing.csv"

if os.path.exists(CSV_FILE):
    try:
        df_standings = pd.read_csv(CSV_FILE)

        # Displays an interactive table without the default row numbers
        st.dataframe(
            df_standings,
            use_container_width=True,
            hide_index=True
        )
    except Exception as e:
        st.error(f"Error reading {CSV_FILE}: {e}")
else:
    st.error(
        f"Could not find `{CSV_FILE}` in your project folder. Make sure the file is named exactly `standings.csv` and placed in your main project folder.")

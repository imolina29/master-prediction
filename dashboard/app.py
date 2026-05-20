import streamlit as st

st.set_page_config(
    page_title="Master Prediction",
    page_icon="⚽",
    layout="wide",
)

st.title("Master Prediction")
st.markdown("### Betting Intelligence Platform")
st.markdown("""
Select a page from the sidebar:

- **League Overview** — Enriched standings with xG and form
- **Team Analysis** — Deep dive into a single team
- **Match Comparator** — Head-to-head comparison
""")

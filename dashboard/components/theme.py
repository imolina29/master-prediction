import streamlit as st

FOOTBALL_CSS = """
<style>
/* ── Sidebar: dark-to-green gradient ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B5E20 0%, #0e1117 60%);
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    color: #c8e6c9;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: rgba(27, 94, 32, 0.12);
    border: 1px solid rgba(46, 125, 50, 0.30);
    border-left: 4px solid #4CAF50;
    border-radius: 10px;
    padding: 16px 20px;
}
[data-testid="stMetricValue"] {
    color: #FFD700 !important;
    font-weight: 700;
}
[data-testid="stMetricDelta"] svg {
    display: inline;
}

/* ── Section headers ── */
h1 {
    color: #4CAF50 !important;
}
h2 {
    color: #66BB6A !important;
    border-bottom: 1px solid rgba(76, 175, 80, 0.25);
    padding-bottom: 6px;
}
h3 {
    color: #81C784 !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(76, 175, 80, 0.15);
    border-radius: 10px;
    overflow: hidden;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    border: 1px solid rgba(76, 175, 80, 0.20);
    border-radius: 10px;
}

/* ── Divider ── */
hr {
    border-color: rgba(76, 175, 80, 0.20) !important;
}

/* ── Selectbox labels ── */
[data-testid="stSelectbox"] label {
    color: #a5d6a7 !important;
}

/* ── Tab styling ── */
[data-testid="stTabs"] button[aria-selected="true"] {
    border-bottom-color: #4CAF50 !important;
    color: #4CAF50 !important;
}

/* ── Info/warning/success boxes ── */
[data-testid="stAlert"] {
    border-radius: 10px;
}
</style>
"""


def apply_theme():
    st.markdown(FOOTBALL_CSS, unsafe_allow_html=True)

import streamlit as st

from dashboard.auth import check_auth, render_user_menu
from dashboard.components.theme import apply_theme

st.set_page_config(page_title="Master Prediction", page_icon="⚽", layout="wide")
apply_theme()

if not check_auth():
    st.stop()

render_user_menu()

nav = st.navigation(
    {
        "": [
            st.Page("pages/0_home.py", title="Home", icon=":material/home:", default=True),
        ],
        "Analisis": [
            st.Page(
                "pages/1_league_overview.py", title="Liga Overview", icon=":material/leaderboard:"
            ),
            st.Page(
                "pages/2_team_analysis.py",
                title="Analisis de Equipo",
                icon=":material/person_search:",
            ),
            st.Page(
                "pages/3_match_comparator.py", title="Comparador", icon=":material/compare_arrows:"
            ),
        ],
        "Predicciones": [
            st.Page("pages/4_predicciones.py", title="Predicciones", icon=":material/psychology:"),
            st.Page("pages/5_value_bets.py", title="Value Bets", icon=":material/payments:"),
        ],
        "Rendimiento": [
            st.Page("pages/6_calibracion.py", title="Calibracion", icon=":material/tune:"),
            st.Page("pages/7_tendencias.py", title="Tendencias", icon=":material/trending_up:"),
        ],
        "Sistema": [
            st.Page("pages/8_admin.py", title="Admin", icon=":material/settings:"),
        ],
    }
)
nav.run()

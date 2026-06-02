import streamlit as st

from dashboard.auth import check_auth, get_current_user, render_user_menu
from dashboard.components.theme import apply_theme

st.set_page_config(page_title="Master Prediction", page_icon="⚽", layout="wide")
apply_theme()

if not check_auth():
    st.stop()

render_user_menu()

user = get_current_user()
is_admin = user and user["role"] == "admin"

pages: dict[str, list] = {
    "": [
        st.Page("views/0_home.py", title="Home", icon=":material/home:", default=True),
    ],
    "Analisis": [
        st.Page("views/1_league_overview.py", title="Liga Overview", icon=":material/leaderboard:"),
        st.Page(
            "views/2_team_analysis.py",
            title="Analisis de Equipo",
            icon=":material/person_search:",
        ),
        st.Page(
            "views/3_match_comparator.py", title="Comparador", icon=":material/compare_arrows:"
        ),
    ],
    "Apuestas": [
        st.Page("views/5_value_bets.py", title="Value Bets", icon=":material/payments:"),
    ],
    "Herramientas": [
        st.Page("views/asesor.py", title="Asesor Virtual", icon=":material/smart_toy:"),
    ],
}

if is_admin:
    pages["Predicciones"] = [
        st.Page("views/4_predicciones.py", title="Predicciones", icon=":material/psychology:"),
    ]
    pages["Rendimiento"] = [
        st.Page("views/6_calibracion.py", title="Calibracion", icon=":material/tune:"),
        st.Page("views/7_tendencias.py", title="Tendencias", icon=":material/trending_up:"),
    ]
    pages["Sistema"] = [
        st.Page("views/8_admin.py", title="Admin", icon=":material/settings:"),
    ]

nav = st.navigation(pages)
nav.run()

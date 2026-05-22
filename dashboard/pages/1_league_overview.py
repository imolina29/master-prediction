import streamlit as st

from dashboard.auth import check_auth
from dashboard.components.tables import form_indicator, standings_table
from dashboard.components.theme import apply_theme
from dashboard.data_access import DIVISION_NAMES, get_seasons, load_matches, load_xg

st.set_page_config(page_title="Vista de Liga", page_icon="📊", layout="wide")
apply_theme()
if not check_auth():
    st.stop()
st.title("📊 Vista de Liga")

col1, col2 = st.columns(2)
with col1:
    league = st.selectbox(
        "Liga", list(DIVISION_NAMES.keys()), format_func=lambda x: DIVISION_NAMES[x]
    )
with col2:
    seasons = get_seasons(league)
    season = st.selectbox("Temporada", seasons if seasons else ["Sin datos"])

if season and season != "Sin datos":
    matches = load_matches(division=league, season=season)
    xg = load_xg(division=league)

    if not matches.empty:
        if not xg.empty:
            xg["match_date"] = xg["match_date"].astype(str)
            matches["match_date_str"] = matches["match_date"].astype(str)
            start_year = int(season[:4])
            xg = xg[
                (xg["match_date"] >= f"{start_year}-07-01")
                & (xg["match_date"] < f"{start_year + 1}-07-01")
            ]

        table = standings_table(matches, xg if not xg.empty else None)

        form_col = []
        for team in table["Equipo"]:
            form_col.append(form_indicator(matches, team))
        table["Racha (ult. 5)"] = form_col

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "xGD": st.column_config.NumberColumn(format="%.1f"),
                "xG": st.column_config.NumberColumn(format="%.1f"),
                "xGA": st.column_config.NumberColumn(format="%.1f"),
            },
        )
    else:
        st.warning("No hay datos para esta temporada.")

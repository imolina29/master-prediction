import streamlit as st

from dashboard.components.tables import form_indicator, standings_table
from dashboard.components.theme import section_header
from dashboard.data_access import DIVISION_NAMES, get_seasons, load_matches, load_xg

st.markdown(
    '<h1 style="font-size:2rem;">📊 Vista de Liga</h1>',
    unsafe_allow_html=True,
)

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

        total_matches = len(matches)
        total_teams = len(table)
        m1, m2, m3 = st.columns(3)
        m1.metric("Equipos", total_teams)
        m2.metric("Partidos", total_matches)
        m3.metric("Temporada", season)

        st.markdown(section_header("🏆", "Tabla de Posiciones"), unsafe_allow_html=True)

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

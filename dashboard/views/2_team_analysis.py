import streamlit as st

from dashboard.components.charts import home_away_chart, xg_vs_goals_chart
from dashboard.components.tables import last_n_results
from dashboard.components.theme import section_header, stat_card
from dashboard.data_access import (
    DIVISION_NAMES,
    get_seasons,
    get_teams,
    load_features,
    load_matches,
)

st.markdown(
    '<h1 style="font-size:2rem;">🔍 Analisis de Equipo</h1>',
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    league = st.selectbox(
        "Liga",
        list(DIVISION_NAMES.keys()),
        format_func=lambda x: DIVISION_NAMES[x],
    )
with col2:
    seasons = get_seasons(league)
    season = st.selectbox("Temporada", seasons if seasons else ["Sin datos"])
with col3:
    sel_season = season if season != "Sin datos" else None
    teams = get_teams(league, season=sel_season)
    team = st.selectbox("Equipo", teams if teams else ["Sin datos"])

if team and team != "Sin datos" and season != "Sin datos":
    matches = load_matches(division=league, season=season)
    features = load_features()

    if not matches.empty:
        home = matches[matches["home_team"] == team]
        away = matches[matches["away_team"] == team]

        total_p = len(home) + len(away)
        total_w = len(home[home["ft_result"] == "H"]) + len(away[away["ft_result"] == "A"])
        total_d = len(home[home["ft_result"] == "D"]) + len(away[away["ft_result"] == "D"])
        total_l = total_p - total_w - total_d
        gf = int(home["ft_home_goals"].sum() + away["ft_away_goals"].sum())
        ga = int(home["ft_away_goals"].sum() + away["ft_home_goals"].sum())

        c1, c2, c3 = st.columns(3)
        with c1:
            win_pct = f"{total_w / total_p:.0%}" if total_p else "—"
            record = f"{total_w}G {total_d}E {total_l}P"
            sub = f"{win_pct} victorias en {total_p} partidos"
            st.markdown(
                stat_card("Rendimiento", record, sub),
                unsafe_allow_html=True,
            )
        with c2:
            diff = gf - ga
            sign = "+" if diff > 0 else ""
            st.markdown(
                stat_card("Goles", f"{gf} / {ga}", f"Diferencia: {sign}{diff}"),
                unsafe_allow_html=True,
            )
        with c3:
            ppg = total_w * 3 + total_d
            ppg_avg = f"{ppg / total_p:.2f}" if total_p else "—"
            st.markdown(
                stat_card("Puntos", str(ppg), f"{ppg_avg} pts/partido"),
                unsafe_allow_html=True,
            )

        if not features.empty:
            team_features = features[features["team"] == team].copy()
            if not team_features.empty:
                team_features["match_date"] = team_features["match_date"].astype(str)
                start_year = int(season[:4])
                team_features = team_features[
                    (team_features["match_date"] >= f"{start_year}-07-01")
                    & (team_features["match_date"] < f"{start_year + 1}-07-01")
                ]
                if not team_features.empty:
                    st.markdown(section_header("📈", "Tendencias"), unsafe_allow_html=True)
                    chart_col1, chart_col2 = st.columns(2)
                    with chart_col1:
                        st.plotly_chart(
                            xg_vs_goals_chart(team_features, team),
                            use_container_width=True,
                        )
                    with chart_col2:
                        st.plotly_chart(
                            home_away_chart(team_features, team),
                            use_container_width=True,
                        )

        st.markdown(section_header("📋", "Ultimos 10 Resultados"), unsafe_allow_html=True)
        results = last_n_results(matches, team, n=10)
        st.dataframe(results, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos disponibles.")

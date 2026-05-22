import streamlit as st

from dashboard.auth import check_auth
from dashboard.components.charts import home_away_chart, xg_vs_goals_chart
from dashboard.components.tables import last_n_results
from dashboard.components.theme import apply_theme
from dashboard.data_access import (
    DIVISION_NAMES,
    get_seasons,
    get_teams,
    load_features,
    load_matches,
)

st.set_page_config(page_title="Analisis de Equipo", page_icon="🔍", layout="wide")
apply_theme()
if not check_auth():
    st.stop()
st.title("🔍 Analisis de Equipo")

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
    teams = get_teams(league)
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

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("PJ", total_p)
        m2.metric("PG", total_w)
        m3.metric("PE", total_d)
        m4.metric("PP", total_l)
        m5.metric("GF", gf)
        m6.metric("GC", ga)

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

        st.subheader("Ultimos 10 Resultados")
        results = last_n_results(matches, team, n=10)
        st.dataframe(results, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos disponibles.")

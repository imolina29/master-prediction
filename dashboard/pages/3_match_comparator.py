import pandas as pd
import streamlit as st

from backend.services.features import compute_h2h_features
from dashboard.components.charts import radar_chart
from dashboard.components.theme import section_header, stat_card
from dashboard.data_access import (
    DIVISION_NAMES,
    get_seasons,
    get_teams,
    load_features,
    load_matches,
)

st.markdown(
    '<h1 style="font-size:2rem;">⚔️ Comparador de Partidos</h1>',
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
    current_season = seasons[0] if seasons else None
    teams = get_teams(league, season=current_season)
    team_a = st.selectbox("Equipo A", teams if teams else ["Sin datos"])
with col3:
    other_teams = [t for t in teams if t != team_a] if teams else ["Sin datos"]
    team_b = st.selectbox("Equipo B", other_teams)

if team_a != "Sin datos" and team_b != "Sin datos":
    matches = load_matches(division=league)
    features = load_features()

    if not matches.empty:
        h2h = compute_h2h_features(matches, team_a, team_b)

        st.markdown(section_header("🤝", "Cabeza a Cabeza"), unsafe_allow_html=True)
        a_key = f"{team_a.lower().replace(' ', '_')}_wins"
        b_key = f"{team_b.lower().replace(' ', '_')}_wins"
        h1, h2, h3 = st.columns(3)
        with h1:
            st.markdown(
                stat_card(team_a, str(h2h.get(a_key, 0)), "victorias"),
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown(
                stat_card("Empates", str(h2h["draws"]), f"de {h2h['total_matches']} partidos"),
                unsafe_allow_html=True,
            )
        with h3:
            st.markdown(
                stat_card(team_b, str(h2h.get(b_key, 0)), "victorias"),
                unsafe_allow_html=True,
            )

        if not features.empty:
            fa = features[features["team"] == team_a]
            fb = features[features["team"] == team_b]

            if not fa.empty and not fb.empty:
                latest_a = fa.sort_values("match_date").iloc[-1]
                latest_b = fb.sort_values("match_date").iloc[-1]

                st.markdown(
                    section_header("📊", "Comparacion de Forma Actual"),
                    unsafe_allow_html=True,
                )
                compare_cols = [
                    "goals_scored_avg",
                    "xg_for_avg",
                    "goals_conceded_avg",
                    "shots_target_avg",
                    "corners_avg",
                    "win_rate",
                ]
                labels = ["Goles", "xG", "Defensa", "Tiros", "Corners", "% Victorias"]

                stats_a = {}
                stats_b = {}
                for col, label in zip(compare_cols, labels):
                    val_a = latest_a.get(col, 0)
                    val_b = latest_b.get(col, 0)
                    stats_a[label] = float(val_a) if pd.notna(val_a) else 0.0
                    stats_b[label] = float(val_b) if pd.notna(val_b) else 0.0

                st.plotly_chart(
                    radar_chart(stats_a, stats_b, team_a, team_b),
                    use_container_width=True,
                )

        st.markdown(section_header("📜", "Historial de Enfrentamientos"), unsafe_allow_html=True)
        h2h_matches = matches[
            ((matches["home_team"] == team_a) & (matches["away_team"] == team_b))
            | ((matches["home_team"] == team_b) & (matches["away_team"] == team_a))
        ].sort_values("match_date", ascending=False)

        if not h2h_matches.empty:
            display_df = h2h_matches[
                [
                    "match_date",
                    "home_team",
                    "away_team",
                    "ft_home_goals",
                    "ft_away_goals",
                    "ft_result",
                ]
            ].copy()
            display_df.columns = ["Fecha", "Local", "Visitante", "GL", "GV", "Resultado"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron enfrentamientos directos.")
    else:
        st.warning("No hay datos disponibles.")

import pandas as pd
import streamlit as st

from backend.services.features import compute_h2h_features
from dashboard.components.charts import radar_chart
from dashboard.data_access import DIVISION_NAMES, get_teams, load_features, load_matches

st.set_page_config(page_title="Comparador de Partidos", layout="wide")
st.title("Comparador de Partidos")

col1, col2, col3 = st.columns(3)
with col1:
    league = st.selectbox(
        "Liga",
        list(DIVISION_NAMES.keys()),
        format_func=lambda x: DIVISION_NAMES[x],
    )
with col2:
    teams = get_teams(league)
    team_a = st.selectbox("Equipo A", teams if teams else ["Sin datos"])
with col3:
    other_teams = [t for t in teams if t != team_a] if teams else ["Sin datos"]
    team_b = st.selectbox("Equipo B", other_teams)

if team_a != "Sin datos" and team_b != "Sin datos":
    matches = load_matches(division=league)
    features = load_features()

    if not matches.empty:
        h2h = compute_h2h_features(matches, team_a, team_b)

        st.subheader("Cabeza a Cabeza")
        h_col1, h_col2, h_col3, h_col4 = st.columns(4)
        h_col1.metric("Total Partidos", h2h["total_matches"])
        a_key = f"{team_a.lower().replace(' ', '_')}_wins"
        b_key = f"{team_b.lower().replace(' ', '_')}_wins"
        h_col2.metric(f"Victorias {team_a}", h2h.get(a_key, 0))
        h_col3.metric(f"Victorias {team_b}", h2h.get(b_key, 0))
        h_col4.metric("Empates", h2h["draws"])

        if not features.empty:
            fa = features[features["team"] == team_a]
            fb = features[features["team"] == team_b]

            if not fa.empty and not fb.empty:
                latest_a = fa.sort_values("match_date").iloc[-1]
                latest_b = fb.sort_values("match_date").iloc[-1]

                st.subheader("Comparacion de Forma Actual")
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

        st.subheader("Historial de Enfrentamientos")
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

import pandas as pd
import streamlit as st

from backend.services.features import compute_h2h_features
from dashboard.components.charts import radar_chart
from dashboard.data_access import DIVISION_NAMES, get_teams, load_features, load_matches

st.set_page_config(page_title="Match Comparator", layout="wide")
st.title("Match Comparator")

col1, col2, col3 = st.columns(3)
with col1:
    league = st.selectbox(
        "League",
        list(DIVISION_NAMES.keys()),
        format_func=lambda x: DIVISION_NAMES[x],
    )
with col2:
    teams = get_teams(league)
    team_a = st.selectbox("Team A", teams if teams else ["No data"])
with col3:
    other_teams = [t for t in teams if t != team_a] if teams else ["No data"]
    team_b = st.selectbox("Team B", other_teams)

if team_a != "No data" and team_b != "No data":
    matches = load_matches(division=league)
    features = load_features()

    if not matches.empty:
        h2h = compute_h2h_features(matches, team_a, team_b)

        st.subheader("Head to Head")
        h_col1, h_col2, h_col3, h_col4 = st.columns(4)
        h_col1.metric("Total Matches", h2h["total_matches"])
        a_key = f"{team_a.lower().replace(' ', '_')}_wins"
        b_key = f"{team_b.lower().replace(' ', '_')}_wins"
        h_col2.metric(f"{team_a} Wins", h2h.get(a_key, 0))
        h_col3.metric(f"{team_b} Wins", h2h.get(b_key, 0))
        h_col4.metric("Draws", h2h["draws"])

        if not features.empty:
            fa = features[features["team"] == team_a]
            fb = features[features["team"] == team_b]

            if not fa.empty and not fb.empty:
                latest_a = fa.sort_values("match_date").iloc[-1]
                latest_b = fb.sort_values("match_date").iloc[-1]

                st.subheader("Current Form Comparison")
                compare_cols = [
                    "goals_scored_avg",
                    "xg_for_avg",
                    "goals_conceded_avg",
                    "shots_target_avg",
                    "corners_avg",
                    "win_rate",
                ]
                labels = ["Goals", "xG", "Defense", "Shots", "Corners", "Win %"]

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

        st.subheader("H2H Match History")
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
            display_df.columns = ["Date", "Home", "Away", "HG", "AG", "Result"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No head-to-head matches found.")
    else:
        st.warning("No match data available.")

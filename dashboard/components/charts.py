import pandas as pd
import plotly.graph_objects as go


def xg_vs_goals_chart(df: pd.DataFrame, team: str) -> go.Figure:
    team_df = df[df["team"] == team].sort_values("match_date")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=team_df["match_date"],
            y=team_df["goals_scored"],
            name="Goles",
            mode="lines+markers",
            line={"color": "#2ecc71"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=team_df["match_date"],
            y=team_df["xg_for"],
            name="xG",
            mode="lines+markers",
            line={"color": "#3498db", "dash": "dash"},
        )
    )
    fig.update_layout(
        title=f"{team} — Goles vs xG",
        xaxis_title="Fecha",
        yaxis_title="Goles / xG",
        template="plotly_dark",
        height=400,
    )
    return fig


def home_away_chart(df: pd.DataFrame, team: str) -> go.Figure:
    home = df[(df["team"] == team) & (df["venue"] == "home")]
    away = df[(df["team"] == team) & (df["venue"] == "away")]

    home_w = home["win"].sum()
    home_d = home["draw"].sum()
    home_l = len(home) - home_w - home_d
    away_w = away["win"].sum()
    away_d = away["draw"].sum()
    away_l = len(away) - away_w - away_d

    x_labels = ["Local", "Visitante"]
    fig = go.Figure(
        data=[
            go.Bar(name="Victorias", x=x_labels, y=[home_w, away_w], marker_color="#2ecc71"),
            go.Bar(name="Empates", x=x_labels, y=[home_d, away_d], marker_color="#f39c12"),
            go.Bar(name="Derrotas", x=x_labels, y=[home_l, away_l], marker_color="#e74c3c"),
        ]
    )
    fig.update_layout(
        barmode="stack",
        title=f"{team} — Local vs Visitante",
        template="plotly_dark",
        height=350,
    )
    return fig


def radar_chart(stats_a: dict, stats_b: dict, team_a: str, team_b: str) -> go.Figure:
    categories = list(stats_a.keys())
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=list(stats_a.values()),
            theta=categories,
            fill="toself",
            name=team_a,
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=list(stats_b.values()),
            theta=categories,
            fill="toself",
            name=team_b,
        )
    )
    fig.update_layout(
        polar={"radialaxis": {"visible": True}},
        title=f"{team_a} vs {team_b}",
        template="plotly_dark",
        height=450,
    )
    return fig

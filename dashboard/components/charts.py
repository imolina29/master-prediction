import pandas as pd
import plotly.graph_objects as go

PLOTLY_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(255,255,255,0.01)",
    "font": {"family": "Inter, sans-serif", "color": "#999", "size": 12},
    "xaxis": {"gridcolor": "rgba(255,255,255,0.03)", "zerolinecolor": "rgba(255,255,255,0.05)"},
    "yaxis": {"gridcolor": "rgba(255,255,255,0.03)", "zerolinecolor": "rgba(255,255,255,0.05)"},
    "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
}

GREEN = "#4CAF50"
GOLD = "#FFD700"
LIGHT_GREEN = "#81C784"
RED = "#E53935"
AMBER = "#FFC107"


def xg_vs_goals_chart(df: pd.DataFrame, team: str) -> go.Figure:
    team_df = df[df["team"] == team].sort_values("match_date")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=team_df["match_date"],
            y=team_df["goals_scored"],
            name="Goles",
            mode="lines+markers",
            line={"color": GREEN},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=team_df["match_date"],
            y=team_df["xg_for"],
            name="xG",
            mode="lines+markers",
            line={"color": GOLD, "dash": "dash"},
        )
    )
    fig.update_layout(
        title=f"{team} — Goles vs xG",
        xaxis_title="Fecha",
        yaxis_title="Goles / xG",
        height=400,
        **PLOTLY_LAYOUT,
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
            go.Bar(name="Victorias", x=x_labels, y=[home_w, away_w], marker_color=GREEN),
            go.Bar(name="Empates", x=x_labels, y=[home_d, away_d], marker_color=AMBER),
            go.Bar(name="Derrotas", x=x_labels, y=[home_l, away_l], marker_color=RED),
        ]
    )
    fig.update_layout(
        barmode="stack",
        title=f"{team} — Local vs Visitante",
        height=350,
        **PLOTLY_LAYOUT,
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
            line={"color": GREEN},
            fillcolor="rgba(76, 175, 80, 0.2)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=list(stats_b.values()),
            theta=categories,
            fill="toself",
            name=team_b,
            line={"color": GOLD},
            fillcolor="rgba(255, 215, 0, 0.2)",
        )
    )
    fig.update_layout(
        polar={"radialaxis": {"visible": True, "gridcolor": "rgba(76,175,80,0.15)"}},
        title=f"{team_a} vs {team_b}",
        height=450,
        **PLOTLY_LAYOUT,
    )
    return fig

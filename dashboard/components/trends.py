import pandas as pd
import plotly.graph_objects as go

from dashboard.data_access import DIVISION_NAMES

PLOTLY_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(14,17,23,0.8)",
    "font": {"color": "#e0e0e0"},
    "height": 420,
}


def _resolved_df(resolved: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(resolved)
    df["match_date"] = pd.to_datetime(df["match_date"])
    df["month"] = df["match_date"].dt.to_period("M").astype(str)
    df["league_name"] = df["division"].map(DIVISION_NAMES).fillna(df["division"])
    df["market_group"] = df["market"].apply(
        lambda m: "1x2" if m.startswith("1x2") else "Over/Under"
    )
    return df


def league_heatmap(resolved: list[dict]) -> go.Figure | None:
    if not resolved:
        return None

    df = _resolved_df(resolved)
    pivot = df.pivot_table(
        values="profit", index="league_name", columns="month", aggfunc="sum", fill_value=0
    )
    pivot = pivot.round(2)

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[
                [0, "#C62828"],
                [0.5, "#1a1a2e"],
                [1, "#2E7D32"],
            ],
            text=pivot.values,
            texttemplate="%{text:+.1f}",
            textfont={"size": 11},
            hovertemplate="Liga: %{y}<br>Mes: %{x}<br>Profit: %{z:+.1f}u<extra></extra>",
        )
    )
    fig.update_layout(
        title="Profit por Liga y Mes",
        xaxis_title="Mes",
        yaxis_title="Liga",
        **PLOTLY_LAYOUT,
    )
    return fig


def market_comparison_chart(resolved: list[dict]) -> go.Figure | None:
    if not resolved:
        return None

    df = _resolved_df(resolved)
    grouped = (
        df.groupby(["month", "market_group"])
        .agg(profit=("profit", "sum"), picks=("profit", "count"))
        .reset_index()
    )

    fig = go.Figure()
    colors = {"1x2": "#4CAF50", "Over/Under": "#FFD700"}
    for mkt in grouped["market_group"].unique():
        mkt_data = grouped[grouped["market_group"] == mkt]
        fig.add_trace(
            go.Bar(
                x=mkt_data["month"],
                y=mkt_data["profit"],
                name=mkt,
                marker_color=colors.get(mkt, "#81C784"),
                hovertemplate=(
                    f"{mkt}<br>Profit: %{{y:+.1f}}u<br>Picks: %{{customdata}}<extra></extra>"
                ),
                customdata=mkt_data["picks"],
            )
        )

    fig.update_layout(
        title="Profit por Mercado y Mes",
        xaxis_title="Mes",
        yaxis_title="Profit (u)",
        barmode="group",
        **PLOTLY_LAYOUT,
    )
    return fig


def profit_timeline(resolved: list[dict]) -> go.Figure | None:
    if not resolved:
        return None

    df = _resolved_df(resolved)
    df = df.sort_values("match_date")

    monthly = (
        df.groupby("month")
        .agg(
            profit=("profit", "sum"),
            picks=("profit", "count"),
        )
        .reset_index()
    )
    monthly["cumulative"] = monthly["profit"].cumsum()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=monthly["month"],
            y=monthly["cumulative"],
            mode="lines+markers",
            name="Profit acumulado",
            line={"color": "#4CAF50", "width": 3},
            marker={"color": "#FFD700", "size": 8},
            fill="tozeroy",
            fillcolor="rgba(76, 175, 80, 0.08)",
        )
    )
    fig.add_trace(
        go.Bar(
            x=monthly["month"],
            y=monthly["picks"],
            name="Picks",
            marker_color="rgba(129, 199, 132, 0.3)",
            yaxis="y2",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)")
    fig.update_layout(
        title="Evolucion Temporal",
        xaxis_title="Mes",
        yaxis_title="Profit acumulado (u)",
        yaxis2={
            "title": "Picks",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
        **PLOTLY_LAYOUT,
    )
    return fig


def stake_analysis_table(resolved: list[dict]) -> pd.DataFrame:
    if not resolved:
        return pd.DataFrame()

    df = pd.DataFrame(resolved)
    grouped = (
        df.groupby("stake")
        .agg(
            picks=("profit", "count"),
            wins=("result", lambda x: (x == "win").sum()),
            profit=("profit", "sum"),
            total_stake=("stake", "sum"),
        )
        .reset_index()
    )

    grouped["hit_rate"] = (grouped["wins"] / grouped["picks"] * 100).round(1)
    grouped["roi"] = (grouped["profit"] / grouped["total_stake"] * 100).round(1)
    grouped["profit"] = grouped["profit"].round(2)

    result = grouped[["stake", "picks", "wins", "hit_rate", "profit", "roi"]].copy()
    result.columns = ["Stake", "Picks", "Ganados", "Acierto %", "Profit (u)", "ROI %"]
    return result.sort_values("Stake", ascending=False).reset_index(drop=True)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def performance_kpis(perf: dict, prev_profit: float = 0) -> None:
    c1, c2, c3, c4 = st.columns(4)
    delta_profit = perf["profit"] - prev_profit if prev_profit else None
    c1.metric(
        "Profit Total",
        f"{perf['profit']:+.2f}u",
        delta=f"{delta_profit:+.2f}u" if delta_profit is not None else None,
    )
    c2.metric("ROI", f"{perf['roi']:.1f}%")
    c3.metric("Tasa de Acierto", f"{perf['hit_rate']:.1%}")
    c4.metric("Picks Resueltos", perf["total_picks"])


def market_breakdown_table(perf: dict) -> pd.DataFrame:
    rows = []
    market_labels = {"1x2": "1X2", "over_under": "Over/Under"}
    for group, data in perf.get("by_market", {}).items():
        rows.append({
            "Mercado": market_labels.get(group, group),
            "Picks": data["picks"],
            "Ganados": data["wins"],
            "ROI": f"{data['roi']:.1f}%",
        })
    return pd.DataFrame(rows)


def profit_chart(resolved: list[dict]) -> go.Figure | None:
    if not resolved:
        return None

    df = pd.DataFrame(resolved)
    df = df.sort_values("match_date")
    df["cumulative_profit"] = df["profit"].cumsum()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["match_date"],
            y=df["cumulative_profit"],
            mode="lines+markers",
            line={"color": "#2ecc71", "width": 2},
            marker={"size": 6},
            name="Profit acumulado",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        title="Profit Acumulado (unidades)",
        xaxis_title="Fecha",
        yaxis_title="Profit (u)",
        template="plotly_dark",
        height=400,
    )
    return fig

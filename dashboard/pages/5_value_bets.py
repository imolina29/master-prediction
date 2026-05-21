import streamlit as st

from backend.betting.tracker import calculate_performance
from dashboard.components.performance import (
    market_breakdown_table,
    performance_kpis,
    profit_chart,
)
from dashboard.components.value_bets import format_picks, format_resolved
from dashboard.data_access import DIVISION_NAMES, get_supabase_client

st.set_page_config(page_title="Value Bets", layout="wide")
st.title("Value Bets")

client = get_supabase_client()

# --- Section 1: Picks del Dia ---
st.header("Picks del Dia")

col1, col2 = st.columns(2)
with col1:
    leagues = ["Todas"] + list(DIVISION_NAMES.keys())
    league_filter = st.selectbox(
        "Liga",
        leagues,
        format_func=lambda x: "Todas las ligas" if x == "Todas" else DIVISION_NAMES.get(x, x),
    )
with col2:
    stake_filter = st.selectbox("Stake minimo", ["Todos", "≥2u", "3u"])

try:
    query = (
        client.table("value_bets")
        .select("*")
        .is_("result", "null")
        .order("match_date")
    )
    if league_filter != "Todas":
        query = query.eq("division", league_filter)
    resp = query.execute()
    active_picks = resp.data or []
except Exception:
    active_picks = []

if stake_filter == "≥2u":
    active_picks = [p for p in active_picks if p["stake"] >= 2]
elif stake_filter == "3u":
    active_picks = [p for p in active_picks if p["stake"] == 3]

if active_picks:
    active_picks.sort(key=lambda p: (-p["edge"], p["match_date"]))
    display = format_picks(active_picks)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption(f"{len(active_picks)} picks activos")
else:
    st.info("No hay picks con valor para los proximos partidos")

# --- Section 2: Rendimiento Historico ---
st.header("Rendimiento Historico")

try:
    resolved_resp = (
        client.table("value_bets")
        .select("*")
        .not_.is_("result", "null")
        .order("match_date", desc=True)
        .execute()
    )
    resolved_picks = resolved_resp.data or []
except Exception:
    resolved_picks = []

if resolved_picks:
    perf = calculate_performance(resolved_picks)
    performance_kpis(perf)

    st.subheader("Desglose por Mercado")
    breakdown = market_breakdown_table(perf)
    if not breakdown.empty:
        st.dataframe(breakdown, use_container_width=True, hide_index=True)

    st.subheader("Profit Acumulado")
    chart = profit_chart(resolved_picks)
    if chart:
        st.plotly_chart(chart, use_container_width=True)

    st.subheader("Ultimos 20 Picks Resueltos")
    recent = resolved_picks[:20]
    resolved_display = format_resolved(recent)
    if not resolved_display.empty:
        st.dataframe(resolved_display, use_container_width=True, hide_index=True)
else:
    st.info(
        "No hay picks resueltos aun. Los picks se resuelven automaticamente"
        " cuando los resultados estan disponibles."
    )

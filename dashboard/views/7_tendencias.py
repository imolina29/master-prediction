import streamlit as st

from backend.betting.tracker import calculate_performance
from dashboard.components.theme import section_header, stat_card
from dashboard.components.trends import (
    league_heatmap,
    market_comparison_chart,
    profit_timeline,
    stake_analysis_table,
)
from dashboard.data_access import get_supabase_client

st.markdown(
    '<h1 style="font-size:2rem;">📈 Tendencias</h1>',
    unsafe_allow_html=True,
)

client = get_supabase_client()

try:
    resp = (
        client.table("value_bets")
        .select("*")
        .not_.is_("result", "null")
        .order("match_date", desc=True)
        .execute()
    )
    resolved = resp.data or []
except Exception:
    resolved = []

if not resolved:
    st.info(
        "No hay suficientes datos para analizar tendencias."
        " Las tendencias se generan a medida que los picks se resuelven."
    )
    st.stop()

perf = calculate_performance(resolved)

# ── KPIs ──
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        stat_card("Total Picks", str(perf["total_picks"]), "resueltos"),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        stat_card("Profit", f"{perf['profit']:+.1f}u", "acumulado"),
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        stat_card("ROI", f"{perf['roi']:.1f}%", "retorno global"),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        stat_card("Acierto", f"{perf['hit_rate']:.0%}", f"{perf['wins']} ganados"),
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Evolucion temporal ──
st.markdown(section_header("📈", "Evolucion Temporal"), unsafe_allow_html=True)
timeline = profit_timeline(resolved)
if timeline:
    st.plotly_chart(timeline, use_container_width=True)

# ── Rendimiento por liga ──
st.markdown(section_header("🏟️", "Rendimiento por Liga"), unsafe_allow_html=True)
heatmap = league_heatmap(resolved)
if heatmap:
    st.plotly_chart(heatmap, use_container_width=True)

# ── Rendimiento por mercado ──
st.markdown(section_header("📊", "Rendimiento por Mercado"), unsafe_allow_html=True)
market_chart = market_comparison_chart(resolved)
if market_chart:
    st.plotly_chart(market_chart, use_container_width=True)

# ── Analisis por stake ──
st.markdown(section_header("🎯", "Analisis por Stake"), unsafe_allow_html=True)
stake_table = stake_analysis_table(resolved)
if not stake_table.empty:
    st.dataframe(stake_table, use_container_width=True, hide_index=True)
    st.caption("¿Los picks de mayor confianza realmente rinden mas?")

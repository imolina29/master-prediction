import pandas as pd
import streamlit as st

from backend.betting.tracker import calculate_performance
from dashboard.components.theme import apply_theme
from dashboard.components.value_bets import _market_label, _result_badge, _stake_badge
from dashboard.data_access import DIVISION_NAMES, get_supabase_client

st.set_page_config(page_title="Master Prediction", page_icon="⚽", layout="wide")
apply_theme()

st.markdown(
    '<h1 style="text-align:center; font-size:2.8rem;">'
    "⚽ Master Prediction"
    "</h1>"
    '<p style="text-align:center; color:#81C784; font-size:1.1rem; margin-top:-10px;">'
    "Plataforma de Inteligencia Deportiva"
    "</p>",
    unsafe_allow_html=True,
)

st.markdown("---")

client = get_supabase_client()

try:
    active_resp = client.table("value_bets").select("*").is_("result", "null").execute()
    active_picks = active_resp.data or []
except Exception:
    active_picks = []

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

recommended = [p for p in active_picks if p["stake"] >= 1]
perf = calculate_performance(resolved_picks) if resolved_picks else None

# ── KPIs ──
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Picks Activos", len(recommended))
with k2:
    st.metric("Profit Total", f"{perf['profit']:+.1f}u" if perf else "—")
with k3:
    st.metric("ROI", f"{perf['roi']:.1f}%" if perf else "—")
with k4:
    st.metric("Tasa de Acierto", f"{perf['hit_rate']:.0%}" if perf else "—")

st.markdown("---")

# ── Picks Recomendados ──
st.header("Picks Recomendados")

if recommended:
    recommended.sort(key=lambda p: (-p["stake"], -p["edge"]))
    rows = []
    for p in recommended[:10]:
        rows.append(
            {
                "Fecha": p["match_date"],
                "Partido": f"{p['home_team']} vs {p['away_team']}",
                "Liga": DIVISION_NAMES.get(p["division"], p["division"]),
                "Apuesta": _market_label(p["market"]),
                "Cuota": f"{p['odd']:.2f}",
                "Ventaja": f"{p['edge']:.1%}",
                "Unidades": _stake_badge(p["stake"]),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"{len(recommended)} picks recomendados activos")
else:
    st.info(
        "No hay picks recomendados actualmente."
        " El pipeline genera picks diariamente a las 6 AM UTC."
    )

# ── Ultimos Resultados + Rendimiento ──
col_left, col_right = st.columns([3, 2])

with col_left:
    st.header("Ultimos Resultados")
    if resolved_picks:
        recent = resolved_picks[:8]
        rows = []
        for p in recent:
            rows.append(
                {
                    "Fecha": p["match_date"],
                    "Partido": f"{p['home_team']} vs {p['away_team']}",
                    "Apuesta": _market_label(p["market"]),
                    "Cuota": f"{p['odd']:.2f}",
                    "Unidades": _stake_badge(p["stake"]),
                    "Resultado": _result_badge(p["result"]),
                    "Ganancia": f"{p['profit']:+.2f}u",
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aun no hay picks resueltos.")

with col_right:
    st.header("Rendimiento")
    if perf:
        st.metric("Picks Resueltos", perf["total_picks"])
        st.metric("Ganados", perf["wins"])
        st.metric("Perdidos", perf["losses"])

        if perf.get("by_market"):
            st.markdown("**Por mercado:**")
            for market_name, data in perf["by_market"].items():
                label = "1x2" if market_name == "1x2" else "Over/Under"
                profit = data["profit"]
                color = "#4CAF50" if profit >= 0 else "#E53935"
                st.markdown(
                    f"- **{label}:** {data['picks']} picks, "
                    f'<span style="color:{color}">{profit:+.1f}u</span>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("El rendimiento se mostrara cuando haya picks resueltos.")

# ── Navegacion rapida ──
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#81C784; font-size:0.9rem;">'
    "📊 Vista de Liga &nbsp;•&nbsp; 🔍 Analisis de Equipo &nbsp;•&nbsp; "
    "⚔️ Comparador &nbsp;•&nbsp; 🤖 Predicciones &nbsp;•&nbsp; 💰 Value Bets"
    "</p>",
    unsafe_allow_html=True,
)

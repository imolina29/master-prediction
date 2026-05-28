import pandas as pd
import streamlit as st

from backend.betting.tracker import calculate_performance
from dashboard.components.predictions import format_predictions
from dashboard.components.theme import section_header, stat_card
from dashboard.components.value_bets import _market_label, _result_badge, _stake_badge
from dashboard.data_access import get_resolved_picks, get_upcoming_predictions

st.markdown(
    '<div style="text-align:center; padding: 1rem 0 0.5rem 0;">'
    '<h1 style="font-size:2.2rem; margin:0; color:#fff !important;'
    " font-weight:800; letter-spacing:-0.03em;"
    '">⚽ Master Prediction</h1>'
    '<p style="color:#555; font-size:0.78rem; margin-top:6px; letter-spacing:0.08em;'
    ' text-transform:uppercase; font-weight:500;">Inteligencia Deportiva con IA</p>'
    "</div>",
    unsafe_allow_html=True,
)

try:
    preds_df = get_upcoming_predictions()
except Exception as e:
    st.error(f"Error al cargar predicciones: {e}")
    preds_df = pd.DataFrame()

try:
    resolved_picks = get_resolved_picks()
except Exception as e:
    st.error(f"Error al cargar picks resueltos: {e}")
    resolved_picks = []

perf = calculate_performance(resolved_picks) if resolved_picks else None

high_conf = 0
if not preds_df.empty and "confidence" in preds_df.columns:
    high_conf = len(preds_df[preds_df["confidence"] == "alta"])

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        stat_card("Predicciones", str(len(preds_df)), "partidos analizados"),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        stat_card("Alta Confianza", str(high_conf), "predicciones"),
        unsafe_allow_html=True,
    )
with k3:
    val = f"{perf['roi']:.1f}%" if perf else "—"
    sub = "retorno de inversion" if perf else ""
    st.markdown(stat_card("ROI", val, sub), unsafe_allow_html=True)
with k4:
    val = f"{perf['hit_rate']:.0%}" if perf else "—"
    sub = f"{perf['wins']}/{perf['total_picks']} picks" if perf else ""
    st.markdown(stat_card("Tasa de Acierto", val, sub), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(section_header("🤖", "Predicciones Proximas"), unsafe_allow_html=True)

if not preds_df.empty:
    display = format_predictions(preds_df)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption(f"{len(preds_df)} predicciones disponibles")
else:
    st.info(
        "No hay predicciones disponibles actualmente."
        " El pipeline genera predicciones diariamente a las 6 AM UTC."
    )

col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown(section_header("📋", "Ultimos Resultados"), unsafe_allow_html=True)
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
    st.markdown(section_header("📈", "Rendimiento"), unsafe_allow_html=True)
    if perf:
        r1, r2 = st.columns(2)
        with r1:
            st.metric("Resueltos", perf["total_picks"])
        with r2:
            st.metric("Ganados", perf["wins"])

        if perf.get("by_market"):
            st.markdown(
                '<p style="color:#666; font-size:0.78rem;'
                " margin:1rem 0 0.5rem 0; text-transform:uppercase;"
                ' letter-spacing:0.06em; font-weight:600;">'
                "Por mercado</p>",
                unsafe_allow_html=True,
            )
            for market_name, data in perf["by_market"].items():
                label = "1x2" if market_name == "1x2" else "Over/Under"
                profit = data["profit"]
                color = "#4CAF50" if profit >= 0 else "#E53935"
                st.markdown(
                    f'<p style="margin:0.3rem 0;">▸ <b>{label}:</b> {data["picks"]} picks · '
                    f'<span style="color:{color};font-weight:600;">{profit:+.1f}u</span></p>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("El rendimiento se mostrara cuando haya picks resueltos.")

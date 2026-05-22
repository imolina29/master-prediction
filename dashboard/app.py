import pandas as pd
import streamlit as st

from backend.betting.tracker import calculate_performance
from dashboard.auth import check_auth
from dashboard.components.theme import apply_theme, section_header, stat_card
from dashboard.components.value_bets import _market_label, _result_badge, _stake_badge
from dashboard.data_access import (
    DIVISION_NAMES,
    FEATURES_PATH,
    PROJECT_ROOT,
    get_supabase_client,
)

st.set_page_config(page_title="Master Prediction", page_icon="⚽", layout="wide")
apply_theme()

if not check_auth():
    st.stop()

# ── Diagnostico temporal (eliminar despues) ──
with st.expander("🔧 Debug info"):
    import sys
    from pathlib import Path

    st.text(f"PROJECT_ROOT: {PROJECT_ROOT}")
    st.text(f"FEATURES_PATH: {FEATURES_PATH}")
    st.text(f"Parquet exists: {FEATURES_PATH.exists()}")
    st.text(f"cwd: {Path.cwd()}")
    st.text(f"data_access.__file__: {__import__('dashboard.data_access', fromlist=['']).__file__}")
    st.text(f"SUPABASE_URL set: {'SUPABASE_URL' in __import__('os').environ}")
    try:
        client = get_supabase_client()
        r = client.table("predictions").select("id").limit(1).execute()
        st.text(f"Supabase OK: {len(r.data)} rows from predictions")
    except Exception as e:
        st.text(f"Supabase error: {e}")
    try:
        r2 = client.table("value_bets").select("id").limit(1).execute()
        st.text(f"value_bets OK: {len(r2.data)} rows")
    except Exception as e:
        st.text(f"value_bets error: {e}")
    sp = [p for p in sys.path if "mount" in p or "master" in p]
    st.text(f"sys.path (relevant): {sp}")

st.markdown(
    '<div style="text-align:center; padding: 1rem 0 0.5rem 0;">'
    '<h1 style="font-size:2.5rem; margin:0;">⚽ Master Prediction</h1>'
    '<p style="color:#81C784; font-size:1rem; margin-top:4px; letter-spacing:2px;'
    ' text-transform:uppercase;">Inteligencia Deportiva con IA</p>'
    "</div>",
    unsafe_allow_html=True,
)

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

# ── KPIs with stat cards ──
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        stat_card("Picks Activos", str(len(recommended)), "recomendados hoy"),
        unsafe_allow_html=True,
    )
with k2:
    val = f"{perf['profit']:+.1f}u" if perf else "—"
    sub = "unidades acumuladas" if perf else ""
    st.markdown(stat_card("Profit Total", val, sub), unsafe_allow_html=True)
with k3:
    val = f"{perf['roi']:.1f}%" if perf else "—"
    sub = "retorno de inversion" if perf else ""
    st.markdown(stat_card("ROI", val, sub), unsafe_allow_html=True)
with k4:
    val = f"{perf['hit_rate']:.0%}" if perf else "—"
    sub = f"{perf['wins']}/{perf['total_picks']} picks" if perf else ""
    st.markdown(stat_card("Tasa de Acierto", val, sub), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Picks Recomendados ──
st.markdown(section_header("🎯", "Picks Recomendados"), unsafe_allow_html=True)

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
                '<p style="color:#a5d6a7; font-size:0.85rem; margin:1rem 0 0.5rem 0;'
                ' text-transform:uppercase; letter-spacing:1px;">Por mercado</p>',
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

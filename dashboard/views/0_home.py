import pandas as pd
import streamlit as st

from dashboard.components.predictions import format_predictions
from dashboard.components.theme import section_header, stat_card
from dashboard.data_access import (
    DIVISION_NAMES,
    get_track_record,
    get_upcoming_predictions,
)

RESULT_LABELS = {"H": "Local", "D": "Empate", "A": "Visitante"}

st.markdown(
    '<div class="hero">'
    '<div style="font-size:2.5rem;margin-bottom:0.3rem;">⚽</div>'
    "<h1>Master Prediction</h1>"
    '<p class="tagline">Inteligencia Deportiva · IA</p>'
    "</div>",
    unsafe_allow_html=True,
)

try:
    preds_df = get_upcoming_predictions()
except Exception as e:
    st.error(f"Error al cargar predicciones: {e}")
    preds_df = pd.DataFrame()

try:
    track = get_track_record(limit=200)
except Exception as e:
    st.error(f"Error al cargar historial: {e}")
    track = pd.DataFrame()

if not track.empty:
    track["hit"] = track["predicted_result"] == track["ft_result"]
    total_resolved = len(track)
    total_hits = int(track["hit"].sum())
    hit_rate = total_hits / total_resolved if total_resolved else 0
else:
    total_resolved = 0
    total_hits = 0
    hit_rate = 0

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
    val = f"{hit_rate:.0%}" if total_resolved else "—"
    sub = f"{total_hits}/{total_resolved}" if total_resolved else ""
    st.markdown(stat_card("Tasa de Acierto", val, sub), unsafe_allow_html=True)
with k4:
    if not track.empty:
        high_track = track[track["confidence"] == "alta"]
        high_hits = int(high_track["hit"].sum()) if not high_track.empty else 0
        high_total = len(high_track)
        val = f"{high_hits / high_total:.0%}" if high_total else "—"
        sub = f"{high_hits}/{high_total} alta confianza" if high_total else ""
    else:
        val = "—"
        sub = ""
    st.markdown(stat_card("Precision Alta Conf.", val, sub), unsafe_allow_html=True)

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
    if not track.empty:
        recent = track.head(10)
        rows = []
        for _, p in recent.iterrows():
            hit = p["predicted_result"] == p["ft_result"]
            badge = "✅ Acertado" if hit else "❌ Fallido"
            score = f"{int(p['ft_home_goals'])}-{int(p['ft_away_goals'])}"
            rows.append(
                {
                    "Fecha": p["match_date"],
                    "Partido": f"{p['home_team']} vs {p['away_team']}",
                    "Marcador": score,
                    "Prediccion": RESULT_LABELS.get(p["predicted_result"], p["predicted_result"]),
                    "Confianza": p.get("confidence", ""),
                    "Resultado": badge,
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aun no hay predicciones resueltas.")

with col_right:
    st.markdown(section_header("📈", "Rendimiento"), unsafe_allow_html=True)
    if not track.empty:
        r1, r2 = st.columns(2)
        with r1:
            st.metric("Resueltos", total_resolved)
        with r2:
            st.metric("Acertados", total_hits)

        by_conf = track.groupby("confidence")["hit"].agg(["sum", "count"])
        if not by_conf.empty:
            st.markdown(
                '<p style="color:#666; font-size:0.78rem;'
                " margin:1rem 0 0.5rem 0; text-transform:uppercase;"
                ' letter-spacing:0.06em; font-weight:600;">'
                "Por confianza</p>",
                unsafe_allow_html=True,
            )
            for conf_label in ["alta", "media", "baja"]:
                if conf_label not in by_conf.index:
                    continue
                hits = int(by_conf.loc[conf_label, "sum"])
                total = int(by_conf.loc[conf_label, "count"])
                rate = hits / total if total else 0
                color = "#4CAF50" if rate >= 0.5 else "#FFC107" if rate >= 0.35 else "#E53935"
                st.markdown(
                    f'<p style="margin:0.3rem 0;">▸ <b>{conf_label.title()}:</b> '
                    f"{hits}/{total} "
                    f'<span style="color:{color};font-weight:600;">'
                    f"({rate:.0%})</span></p>",
                    unsafe_allow_html=True,
                )

        by_div = track.groupby("division")["hit"].agg(["sum", "count"])
        if len(by_div) > 1:
            st.markdown(
                '<p style="color:#666; font-size:0.78rem;'
                " margin:1rem 0 0.5rem 0; text-transform:uppercase;"
                ' letter-spacing:0.06em; font-weight:600;">'
                "Por liga</p>",
                unsafe_allow_html=True,
            )
            for div_code in by_div.index:
                hits = int(by_div.loc[div_code, "sum"])
                total = int(by_div.loc[div_code, "count"])
                rate = hits / total if total else 0
                color = "#4CAF50" if rate >= 0.5 else "#FFC107" if rate >= 0.35 else "#E53935"
                name = DIVISION_NAMES.get(div_code, div_code)
                st.markdown(
                    f'<p style="margin:0.3rem 0;">▸ <b>{name}:</b> '
                    f"{hits}/{total} "
                    f'<span style="color:{color};font-weight:600;">'
                    f"({rate:.0%})</span></p>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("El rendimiento se mostrara cuando haya predicciones resueltas.")

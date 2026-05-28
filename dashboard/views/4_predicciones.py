from datetime import date, timedelta

import pandas as pd
import streamlit as st

from backend.ml.config import BACKTEST_RESULTS_PATH
from dashboard.components.metrics import (
    backtest_summary_table,
    calibration_chart,
    load_backtest_results,
)
from dashboard.components.predictions import format_predictions
from dashboard.components.theme import section_header, stat_card
from dashboard.data_access import DIVISION_NAMES, get_supabase_client

st.markdown(
    '<h1 style="font-size:2rem;">🤖 Predicciones</h1>',
    unsafe_allow_html=True,
)

# --- Section 1: Upcoming predictions ---
st.markdown(section_header("🔮", "Proximas Predicciones"), unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    leagues = ["Todas"] + list(DIVISION_NAMES.keys())
    league_filter = st.selectbox(
        "Liga",
        leagues,
        format_func=lambda x: "Todas las ligas" if x == "Todas" else DIVISION_NAMES.get(x, x),
    )
with col2:
    confidence_filter = st.selectbox("Confianza", ["Todas", "alta", "media"])
with col3:
    date_range = st.date_input(
        "Rango de fechas",
        value=(date.today(), date.today() + timedelta(days=21)),
        format="YYYY-MM-DD",
    )

try:
    client = get_supabase_client()
    query = client.table("predictions").select("*").order("match_date")
    if league_filter != "Todas":
        query = query.eq("division", league_filter)
    if confidence_filter != "Todas":
        query = query.eq("confidence", confidence_filter)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        query = query.gte("match_date", str(date_range[0])).lte("match_date", str(date_range[1]))
    resp = query.limit(200).execute()
    preds_df = pd.DataFrame(resp.data)
except Exception as e:
    st.error(f"Error al cargar predicciones: {e}")
    preds_df = pd.DataFrame()

if not preds_df.empty:
    if "confidence" in preds_df.columns:
        high_conf = len(preds_df[preds_df["confidence"] == "alta"])
    else:
        high_conf = 0
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(
            stat_card("Predicciones", str(len(preds_df)), "partidos analizados"),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            stat_card("Alta Confianza", str(high_conf), "predicciones"),
            unsafe_allow_html=True,
        )

    display = format_predictions(preds_df)
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No hay predicciones disponibles para el rango seleccionado.")

# --- Section 2: Model metrics ---
st.markdown(section_header("📊", "Metricas del Modelo"), unsafe_allow_html=True)

results = load_backtest_results(BACKTEST_RESULTS_PATH)

if results:
    model_names = list(results.keys())

    total_folds = sum(len(d.get("folds", [])) for d in results.values())
    best_acc = max((d.get("mean_accuracy", 0) for d in results.values()), default=0)
    roi_vals = [d["mean_roi_pct"] for d in results.values() if "mean_roi_pct" in d]
    best_roi = max(roi_vals) if roi_vals else 0

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            stat_card("Mejor Accuracy", f"{best_acc:.1%}", "precision del modelo"),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            stat_card("Mejor ROI", f"{best_roi:.1f}%", "retorno simulado"),
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            stat_card("Evaluaciones", str(total_folds), "folds de backtesting"),
            unsafe_allow_html=True,
        )

    st.markdown(section_header("📋", "Resumen por Modelo"), unsafe_allow_html=True)
    summary = backtest_summary_table(results)
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.markdown(section_header("📈", "Rendimiento por Temporada"), unsafe_allow_html=True)
    selected_model = st.selectbox("Modelo", model_names)
    chart = calibration_chart(results, selected_model)
    if chart:
        st.plotly_chart(chart, use_container_width=True)
else:
    st.info("No hay resultados de backtesting. Ejecuta el entrenamiento primero.")

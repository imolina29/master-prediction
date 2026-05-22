from datetime import date, timedelta

import pandas as pd
import streamlit as st

from backend.ml.config import BACKTEST_RESULTS_PATH
from dashboard.auth import check_auth
from dashboard.components.metrics import (
    backtest_summary_table,
    calibration_chart,
    load_backtest_results,
)
from dashboard.components.predictions import format_predictions
from dashboard.components.theme import apply_theme
from dashboard.data_access import DIVISION_NAMES, get_supabase_client

st.set_page_config(page_title="Predicciones", page_icon="🤖", layout="wide")
apply_theme()
if not check_auth():
    st.stop()
st.title("🤖 Predicciones")

# --- Section 1: Upcoming predictions ---
st.header("Proximas Predicciones")

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
        value=(date.today(), date.today() + timedelta(days=7)),
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
except Exception:
    preds_df = pd.DataFrame()

if not preds_df.empty:
    display = format_predictions(preds_df)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption(f"{len(preds_df)} predicciones mostradas")
else:
    st.info("No hay predicciones disponibles para el rango seleccionado.")

# --- Section 2: Model metrics ---
st.header("Metricas del Modelo")

results = load_backtest_results(BACKTEST_RESULTS_PATH)

if results:
    model_names = list(results.keys())

    total_folds = sum(len(d.get("folds", [])) for d in results.values())
    best_acc = max((d.get("mean_accuracy", 0) for d in results.values()), default=0)
    roi_vals = [d["mean_roi_pct"] for d in results.values() if "mean_roi_pct" in d]
    best_roi = max(roi_vals) if roi_vals else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Mejor Accuracy", f"{best_acc:.1%}")
    m2.metric("Mejor ROI", f"{best_roi:.1f}%")
    m3.metric("Total Evaluaciones", total_folds)

    st.subheader("Resumen por Modelo")
    summary = backtest_summary_table(results)
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.subheader("Rendimiento por Temporada")
    selected_model = st.selectbox("Modelo", model_names)
    chart = calibration_chart(results, selected_model)
    if chart:
        st.plotly_chart(chart, use_container_width=True)
else:
    st.info("No hay resultados de backtesting. Ejecuta el entrenamiento primero.")

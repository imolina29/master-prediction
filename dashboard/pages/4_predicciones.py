import pandas as pd
import streamlit as st

from backend.ml.config import BACKTEST_RESULTS_PATH
from dashboard.components.metrics import (
    backtest_summary_table,
    calibration_chart,
    load_backtest_results,
)
from dashboard.components.predictions import format_predictions
from dashboard.data_access import DIVISION_NAMES, get_supabase_client

st.set_page_config(page_title="Predicciones", layout="wide")
st.title("Predicciones")

# --- Section 1: Upcoming predictions ---
st.header("Proximas Predicciones")

col1, col2 = st.columns(2)
with col1:
    leagues = ["Todas"] + list(DIVISION_NAMES.keys())
    league_filter = st.selectbox(
        "Liga",
        leagues,
        format_func=lambda x: "Todas las ligas" if x == "Todas" else DIVISION_NAMES.get(x, x),
    )
with col2:
    confidence_filter = st.selectbox("Confianza", ["Todas", "alta", "media"])

try:
    client = get_supabase_client()
    query = client.table("predictions").select("*").order("match_date")
    if league_filter != "Todas":
        query = query.eq("division", league_filter)
    if confidence_filter != "Todas":
        query = query.eq("confidence", confidence_filter)
    resp = query.limit(100).execute()
    preds_df = pd.DataFrame(resp.data)
except Exception:
    preds_df = pd.DataFrame()

if not preds_df.empty:
    display = format_predictions(preds_df)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption(f"{len(preds_df)} predicciones mostradas")
else:
    st.info("No hay predicciones disponibles. Ejecuta el pipeline de predicciones primero.")

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

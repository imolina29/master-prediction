import streamlit as st

from backend.ml.config import BACKTEST_RESULTS_PATH
from dashboard.auth import check_auth
from dashboard.components.calibration import (
    build_calibration_data,
    model_comparison_chart,
)
from dashboard.components.metrics import load_backtest_results
from dashboard.components.theme import apply_theme

st.set_page_config(page_title="Calibracion", page_icon="🎯", layout="wide")
apply_theme()
if not check_auth():
    st.stop()
st.title("🎯 Calibracion del Modelo")

results = load_backtest_results(BACKTEST_RESULTS_PATH)

if not results:
    st.info("No hay resultados de backtesting disponibles. Ejecuta el entrenamiento primero.")
    st.stop()

# ── Comparacion de modelos ──
st.header("Comparacion de Modelos")

comparison = model_comparison_chart(results)
st.plotly_chart(comparison, use_container_width=True)

# ── KPIs por modelo ──
col1, col2, col3 = st.columns(3)
best_acc = max((d.get("mean_accuracy", 0) for d in results.values()), default=0)
best_model = max(results, key=lambda k: results[k].get("mean_accuracy", 0))
roi_vals = [d["mean_roi_pct"] for d in results.values() if "mean_roi_pct" in d]
best_roi = max(roi_vals) if roi_vals else 0

with col1:
    st.metric("Mejor Accuracy", f"{best_acc:.1%}")
with col2:
    st.metric("Mejor ROI", f"{best_roi:.1f}%")
with col3:
    st.metric("Mejor Modelo", best_model)

# ── Detalle por modelo y temporada ──
st.header("Detalle por Temporada")

cal_data = build_calibration_data(results)
if not cal_data.empty:
    model_names = sorted(cal_data["modelo"].unique())
    selected = st.selectbox("Modelo", model_names)

    model_data = cal_data[cal_data["modelo"] == selected]

    display = model_data[["temporada", "accuracy", "log_loss", "n_test"]].copy()
    display.columns = ["Temporada", "Accuracy", "Log Loss", "Muestras Test"]
    display["Accuracy"] = display["Accuracy"].apply(lambda x: f"{x:.1%}")
    display["Log Loss"] = display["Log Loss"].apply(lambda x: f"{x:.4f}")

    if "roi_pct" in model_data.columns and model_data["roi_pct"].notna().any():
        display["ROI"] = model_data["roi_pct"].apply(
            lambda x: f"{x:.1f}%" if x is not None else "—"
        )

    if "brier_score" in model_data.columns and model_data["brier_score"].notna().any():
        display["Brier Score"] = model_data["brier_score"].apply(
            lambda x: f"{x:.4f}" if x is not None else "—"
        )

    st.dataframe(display, use_container_width=True, hide_index=True)

    mean_acc = model_data["accuracy"].mean()
    mean_ll = model_data["log_loss"].mean()
    st.caption(f"Promedio — Accuracy: {mean_acc:.1%} | Log Loss: {mean_ll:.4f}")

# ── Guia de interpretacion ──
with st.expander("Guia de interpretacion"):
    st.markdown(
        "- **Accuracy:** Porcentaje de predicciones correctas. Mayor es mejor.\n"
        "- **Log Loss:** Calidad de las probabilidades predichas."
        " Menor es mejor (0 = perfecto).\n"
        "- **Brier Score:** Error cuadratico de las probabilidades."
        " Menor es mejor (0 = perfecto).\n"
        "- **ROI:** Retorno simulado apostando cuando el modelo detecta ventaja (>5% edge).\n"
        "- **Calibracion perfecta:** Cuando el modelo dice 60%, ocurre 60% de las veces."
    )

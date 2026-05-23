import streamlit as st

from backend.ml.config import BACKTEST_RESULTS_PATH
from dashboard.components.calibration import (
    build_calibration_data,
    model_comparison_chart,
)
from dashboard.components.metrics import load_backtest_results
from dashboard.components.theme import section_header, stat_card

st.markdown(
    '<h1 style="font-size:2rem;">🎯 Calibracion del Modelo</h1>',
    unsafe_allow_html=True,
)

results = load_backtest_results(BACKTEST_RESULTS_PATH)

if not results:
    st.info("No hay resultados de backtesting disponibles. Ejecuta el entrenamiento primero.")
    st.stop()

# ── Comparacion de modelos ──
st.markdown(section_header("📊", "Comparacion de Modelos"), unsafe_allow_html=True)

comparison = model_comparison_chart(results)
st.plotly_chart(comparison, use_container_width=True)

# ── KPIs por modelo ──
best_acc = max((d.get("mean_accuracy", 0) for d in results.values()), default=0)
best_model = max(results, key=lambda k: results[k].get("mean_accuracy", 0))
roi_vals = [d["mean_roi_pct"] for d in results.values() if "mean_roi_pct" in d]
best_roi = max(roi_vals) if roi_vals else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        stat_card("Mejor Accuracy", f"{best_acc:.1%}", "precision global"),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        stat_card("Mejor ROI", f"{best_roi:.1f}%", "retorno simulado"),
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        stat_card("Mejor Modelo", best_model, "por accuracy"),
        unsafe_allow_html=True,
    )

# ── Detalle por modelo y temporada ──
st.markdown(section_header("📋", "Detalle por Temporada"), unsafe_allow_html=True)

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
with st.expander("📖 Guia de interpretacion"):
    st.markdown(
        "- **Accuracy:** Porcentaje de predicciones correctas. Mayor es mejor.\n"
        "- **Log Loss:** Calidad de las probabilidades predichas."
        " Menor es mejor (0 = perfecto).\n"
        "- **Brier Score:** Error cuadratico de las probabilidades."
        " Menor es mejor (0 = perfecto).\n"
        "- **ROI:** Retorno simulado apostando cuando el modelo detecta ventaja (>5% edge).\n"
        "- **Calibracion perfecta:** Cuando el modelo dice 60%, ocurre 60% de las veces."
    )

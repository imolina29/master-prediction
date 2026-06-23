from datetime import date, timedelta

import pandas as pd
import streamlit as st

from backend.ml.config import BACKTEST_RESULTS_PATH
from dashboard.components.metrics import (
    backtest_summary_table,
    calibration_chart,
    load_backtest_results,
)
from dashboard.components.theme import (
    eyebrow,
    page_title,
    prediction_card,
    section_header,
    stat_card,
)
from dashboard.data_access import DIVISION_NAMES, get_supabase_client, get_track_record

st.markdown(eyebrow("Analisis · Modelo probabilistico"), unsafe_allow_html=True)
st.markdown(
    page_title("Predicciones", "Probabilidades 1X2, goles esperados y BTTS por partido."),
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    leagues = ["Todas"] + list(DIVISION_NAMES.keys())
    league_filter = st.selectbox(
        "Liga",
        leagues,
        format_func=lambda x: "Todas las ligas" if x == "Todas" else DIVISION_NAMES.get(x, x),
    )
with col2:
    confidence_filter = st.selectbox("Confianza", ["Todas", "alta", "media", "baja"])
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
    alta = (
        len(preds_df[preds_df["confidence"] == "alta"]) if "confidence" in preds_df.columns else 0
    )
    media = (
        len(preds_df[preds_df["confidence"] == "media"]) if "confidence" in preds_df.columns else 0
    )
    baja = (
        len(preds_df[preds_df["confidence"] == "baja"]) if "confidence" in preds_df.columns else 0
    )

    filter_html = (
        f'<div class="mp-filter-pills">'
        f'<span class="mp-filter-pill active">'
        f'Todas <span class="count">{len(preds_df)}</span></span>'
        f'<span class="mp-filter-pill">Alta <span class="count">{alta}</span></span>'
        f'<span class="mp-filter-pill">Media <span class="count">{media}</span></span>'
        f'<span class="mp-filter-pill">Baja <span class="count">{baja}</span></span>'
        f"</div>"
    )
    st.markdown(filter_html, unsafe_allow_html=True)

    m1, m2 = st.columns(2)
    with m1:
        st.markdown(
            stat_card("Predicciones", str(len(preds_df)), "partidos analizados"),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            stat_card(
                "Alta Confianza",
                str(alta),
                "predicciones",
                progress=alta / len(preds_df) * 100 if len(preds_df) > 0 else 0,
            ),
            unsafe_allow_html=True,
        )

    cols = st.columns(2)
    for i, (_, p) in enumerate(preds_df.iterrows()):
        with cols[i % 2]:
            league = DIVISION_NAMES.get(p.get("division", ""), p.get("division", ""))
            st.markdown(
                prediction_card(
                    home=p["home_team"],
                    away=p["away_team"],
                    date=str(p["match_date"]),
                    league=league,
                    prob_h=p.get("prob_home", 0),
                    prob_d=p.get("prob_draw", 0),
                    prob_a=p.get("prob_away", 0),
                    predicted=p.get("predicted_result", ""),
                    confidence=p.get("confidence", "baja"),
                    prob_over25=p.get("prob_over25"),
                    prob_btts=p.get("prob_btts"),
                ),
                unsafe_allow_html=True,
            )
else:
    st.info("No hay predicciones disponibles para el rango seleccionado.")

st.markdown(section_header("📋", "Track Record"), unsafe_allow_html=True)

try:
    track_df = get_track_record(limit=100)
except Exception as e:
    st.error(f"Error al cargar track record: {e}")
    track_df = pd.DataFrame()

if not track_df.empty:
    result_map = {"H": "Local", "D": "Empate", "A": "Visitante"}
    track_df["predicted_label"] = track_df["predicted_result"].map(result_map)
    track_df["actual_label"] = track_df["ft_result"].map(result_map)
    track_df["correct"] = track_df["predicted_result"] == track_df["ft_result"]

    total = len(track_df)
    hits = track_df["correct"].sum()
    hit_rate = hits / total if total > 0 else 0

    alta_mask = track_df["confidence"] == "alta"
    alta_total = alta_mask.sum()
    alta_hits = track_df.loc[alta_mask, "correct"].sum()
    alta_rate = alta_hits / alta_total if alta_total > 0 else 0

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            stat_card(
                "Aciertos",
                f"{hit_rate:.0%}",
                f"{hits}/{total} predicciones",
                progress=hit_rate * 100,
            ),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            stat_card(
                "Alta Confianza",
                f"{alta_rate:.0%}",
                f"{alta_hits}/{alta_total} aciertos",
                progress=alta_rate * 100,
                featured=alta_rate > 0.5,
            ),
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            stat_card("Partidos Analizados", str(total), "con resultado"),
            unsafe_allow_html=True,
        )

    display = track_df[
        [
            "match_date",
            "home_team",
            "away_team",
            "division",
            "prob_home",
            "prob_draw",
            "prob_away",
            "predicted_label",
            "actual_label",
            "correct",
            "confidence",
        ]
    ].copy()

    display[""] = display["correct"].apply(lambda x: "✅" if x else "❌")
    for col in ["prob_home", "prob_draw", "prob_away"]:
        display[col] = display[col].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "-")
    display["division"] = display["division"].map(DIVISION_NAMES).fillna(display["division"])

    display = display[
        [
            "match_date",
            "home_team",
            "away_team",
            "division",
            "prob_home",
            "prob_draw",
            "prob_away",
            "predicted_label",
            "actual_label",
            "",
            "confidence",
        ]
    ]
    display.columns = [
        "Fecha",
        "Local",
        "Visitante",
        "Liga",
        "P(H)",
        "P(D)",
        "P(A)",
        "Prediccion",
        "Resultado",
        "",
        "Confianza",
    ]

    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("Aun no hay predicciones con resultado para mostrar el track record.")

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
            stat_card(
                "Mejor Accuracy",
                f"{best_acc:.1%}",
                "precision del modelo",
                progress=best_acc * 100,
            ),
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

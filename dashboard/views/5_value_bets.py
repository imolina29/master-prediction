from datetime import date, timedelta

import streamlit as st

from backend.betting.tracker import calculate_performance
from backend.betting.value import calculate_edge
from dashboard.components.performance import (
    market_breakdown_table,
    performance_kpis,
    profit_chart,
)
from dashboard.components.theme import section_header, stat_card
from dashboard.components.value_bets import format_picks, format_resolved
from dashboard.data_access import DIVISION_NAMES, get_resolved_picks, get_supabase_client

st.markdown(
    '<h1 style="font-size:2rem;">💰 Value Bets</h1>',
    unsafe_allow_html=True,
)

with st.expander("📖 Guia de terminos"):
    st.markdown(
        "- **Apuesta:** Tipo de apuesta (Local, Empate, Visitante, Over/Under 2.5)\n"
        "- **Cuota:** Precio ofrecido por las casas de apuestas\n"
        "- **Ventaja:** Diferencia entre la probabilidad del modelo y la del mercado."
        " A mayor ventaja, mayor oportunidad\n"
        "- **Unidades:** Cantidad sugerida a apostar"
        " (1u = minima, 2u = media, 3u = alta confianza,"
        " Sin valor = no recomendado)\n"
        "- **Valor Esperado:** Ganancia esperada por unidad apostada."
        " Positivo = apuesta rentable a largo plazo\n"
        "- **Ganancia:** Resultado real de la apuesta en unidades"
    )

client = get_supabase_client()

# --- Section 1: Picks del Dia ---
st.markdown(section_header("🎯", "Analisis de Partidos"), unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    leagues = ["Todas"] + list(DIVISION_NAMES.keys())
    league_filter = st.selectbox(
        "Liga",
        leagues,
        format_func=lambda x: "Todas las ligas" if x == "Todas" else DIVISION_NAMES.get(x, x),
    )
with col2:
    stake_filter = st.selectbox("Filtro", ["Todos los partidos", "Solo recomendados", "≥2u", "3u"])
with col3:
    date_range = st.date_input(
        "Rango de fechas",
        value=(date.today(), date.today() + timedelta(days=7)),
        format="YYYY-MM-DD",
    )

# Fetch value bets (picks with edge)
try:
    query = client.table("value_bets").select("*").is_("result", "null").order("match_date")
    if league_filter != "Todas":
        query = query.eq("division", league_filter)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        query = query.gte("match_date", str(date_range[0])).lte("match_date", str(date_range[1]))
    resp = query.execute()
    value_bets = resp.data or []
except Exception as e:
    st.error(f"Error al cargar value bets: {e}")
    value_bets = []

# Fetch predictions + odds for matches WITHOUT value bets
try:
    pred_query = client.table("predictions").select("*")
    if league_filter != "Todas":
        pred_query = pred_query.eq("division", league_filter)
    pred_resp = pred_query.execute()
    predictions = pred_resp.data or []

    match_query = (
        client.table("matches")
        .select(
            "match_date, home_team, away_team, division,"
            " odd_home, odd_draw, odd_away, odd_over25, odd_under25"
        )
        .is_("ft_result", "null")
    )
    if league_filter != "Todas":
        match_query = match_query.eq("division", league_filter)
    match_resp = match_query.execute()
    matches_with_odds = {
        (m["match_date"], m["home_team"], m["away_team"]): m for m in (match_resp.data or [])
    }
except Exception as e:
    st.error(f"Error al cargar predicciones: {e}")
    predictions = []
    matches_with_odds = {}

# Build "no value" rows for predictions that have odds but no value bet
vb_keys = {(vb["match_date"], vb["home_team"], vb["away_team"]) for vb in value_bets}

no_value_rows = []
for pred in predictions:
    key = (pred["match_date"], pred["home_team"], pred["away_team"])
    if key in vb_keys:
        continue
    odds = matches_with_odds.get(key)
    if not odds or not odds.get("odd_home"):
        continue

    h2h_odds = [odds.get("odd_home"), odds.get("odd_draw"), odds.get("odd_away")]
    result_map = {"H": ("1x2_home", "H", pred["prob_home"], h2h_odds, 0)}
    if pred.get("predicted_result") == "D":
        result_map = {"D": ("1x2_draw", "D", pred["prob_draw"], h2h_odds, 1)}
    elif pred.get("predicted_result") == "A":
        result_map = {"A": ("1x2_away", "A", pred["prob_away"], h2h_odds, 2)}

    for _, (market, selection, model_prob, mkt_odds, sel_idx) in result_map.items():
        if not model_prob or not mkt_odds[sel_idx]:
            continue
        calc = calculate_edge(model_prob, sel_idx, mkt_odds)
        no_value_rows.append(
            {
                "match_date": pred["match_date"],
                "home_team": pred["home_team"],
                "away_team": pred["away_team"],
                "division": pred["division"],
                "market": market,
                "selection": selection,
                "edge": calc["edge"],
                "odd": mkt_odds[sel_idx],
                "stake": 0,
                "expected_value": calc["expected_value"],
            }
        )

# Combine and filter
all_rows = value_bets + no_value_rows

if stake_filter == "Solo recomendados":
    all_rows = [p for p in all_rows if p["stake"] >= 1]
elif stake_filter == "≥2u":
    all_rows = [p for p in all_rows if p["stake"] >= 2]
elif stake_filter == "3u":
    all_rows = [p for p in all_rows if p["stake"] == 3]

if all_rows:
    recommended = sum(1 for p in all_rows if p["stake"] >= 1)
    total = len(all_rows)

    m1, m2 = st.columns(2)
    with m1:
        st.markdown(
            stat_card("Partidos Analizados", str(total), "con prediccion y cuotas"),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            stat_card("Recomendados", str(recommended), "con ventaja positiva"),
            unsafe_allow_html=True,
        )

    all_rows.sort(key=lambda p: (-p["stake"], -p["edge"], p["match_date"]))
    display = format_picks(all_rows)
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No hay partidos con predicciones y cuotas disponibles")

# --- Section 2: Rendimiento Historico ---
st.markdown(section_header("📈", "Rendimiento Historico"), unsafe_allow_html=True)

try:
    resolved_picks = get_resolved_picks()
except Exception as e:
    st.error(f"Error al cargar historial: {e}")
    resolved_picks = []

if resolved_picks:
    perf = calculate_performance(resolved_picks)
    performance_kpis(perf)

    st.markdown(section_header("📊", "Desglose por Mercado"), unsafe_allow_html=True)
    breakdown = market_breakdown_table(perf)
    if not breakdown.empty:
        st.dataframe(breakdown, use_container_width=True, hide_index=True)

    st.markdown(section_header("💰", "Profit Acumulado"), unsafe_allow_html=True)
    chart = profit_chart(resolved_picks)
    if chart:
        st.plotly_chart(chart, use_container_width=True)

    st.markdown(section_header("📋", "Ultimos 20 Picks Resueltos"), unsafe_allow_html=True)
    recent = resolved_picks[:20]
    resolved_display = format_resolved(recent)
    if not resolved_display.empty:
        st.dataframe(resolved_display, use_container_width=True, hide_index=True)
else:
    st.info(
        "No hay picks resueltos aun. Los picks se resuelven automaticamente"
        " cuando los resultados estan disponibles."
    )

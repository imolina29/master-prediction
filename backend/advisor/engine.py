"""Advisor engine — intent parsing, data lookup, and template responses."""

import logging
import re
import unicodedata
from datetime import date, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

TEAM_ALIASES = {
    "psg": "Paris SG",
    "paris": "Paris SG",
    "paris saint germain": "Paris SG",
    "barca": "Barcelona",
    "barça": "Barcelona",
    "real": "Real Madrid",
    "madrid": "Real Madrid",
    "atletico": "Ath Madrid",
    "atleti": "Ath Madrid",
    "bayern": "Bayern Munich",
    "juve": "Juventus",
    "inter": "Inter Milan",
    "milan": "AC Milan",
    "ac milan": "AC Milan",
    "man city": "Manchester City",
    "city": "Manchester City",
    "man utd": "Manchester Utd",
    "united": "Manchester Utd",
    "liverpool": "Liverpool",
    "chelsea": "Chelsea",
    "arsenal": "Arsenal",
    "tottenham": "Tottenham",
    "spurs": "Tottenham",
    "napoli": "Napoli",
    "dortmund": "Dortmund",
    "benfica": "Benfica",
    "porto": "Porto",
    "sporting": "Sporting CP",
    "ajax": "Ajax",
    "feyenoord": "Feyenoord",
    "usa": "United States",
    "eeuu": "United States",
    "estados unidos": "United States",
    "corea": "South Korea",
    "corea del sur": "South Korea",
    "costa de marfil": "Ivory Coast",
    "alemania": "Germany",
    "francia": "France",
    "españa": "Spain",
    "italia": "Italy",
    "inglaterra": "England",
    "brasil": "Brazil",
    "mexico": "Mexico",
    "méxico": "Mexico",
    "argentina": "Argentina",
    "colombia": "Colombia",
    "portugal": "Portugal",
    "holanda": "Netherlands",
    "paises bajos": "Netherlands",
    "belgica": "Belgium",
    "bélgica": "Belgium",
    "suiza": "Switzerland",
    "croacia": "Croatia",
    "dinamarca": "Denmark",
    "suecia": "Sweden",
    "noruega": "Norway",
    "turquia": "Turkey",
    "turquía": "Turkey",
    "japon": "Japan",
    "japón": "Japan",
    "australia": "Australia",
    "canada": "Canada",
    "canadá": "Canada",
    "uruguay": "Uruguay",
    "paraguay": "Paraguay",
    "ecuador": "Ecuador",
    "marruecos": "Morocco",
    "senegal": "Senegal",
    "egipto": "Egypt",
    "argelia": "Algeria",
    "tunez": "Tunisia",
    "túnez": "Tunisia",
    "ghana": "Ghana",
    "panama": "Panama",
    "panamá": "Panama",
    "haiti": "Haiti",
    "haití": "Haiti",
    "escocia": "Scotland",
    "gales": "Wales",
    "irlanda": "Ireland",
    "iran": "Iran",
    "irán": "Iran",
    "irak": "Iraq",
    "qatar": "Qatar",
    "arabia saudita": "Saudi Arabia",
    "nueva zelanda": "New Zealand",
    "austria": "Austria",
    "jordania": "Jordan",
    "uzbekistan": "Uzbekistan",
    "bolivia": "Bolivia",
    "peru": "Peru",
    "perú": "Peru",
    "chile": "Chile",
    "venezuela": "Venezuela",
    "serbia": "Serbia",
    "rumania": "Romania",
    "ucrania": "Ukraine",
    "republica checa": "Czechia",
    "chequia": "Czechia",
    "sudafrica": "South Africa",
    "sudáfrica": "South Africa",
    "curacao": "Curacao",
    "cabo verde": "Cape Verde Islands",
    "congo": "Congo DR",
    "bosnia": "Bosnia Herzegovina",
}

BEST_PICKS_KEYWORDS = [
    "mejor",
    "mejores",
    "recomendar",
    "recomendacion",
    "apostar",
    "apuesta",
    "pick",
    "picks",
    "seguro",
    "segura",
    "confianza",
    "alta confianza",
    "top",
]

DATE_KEYWORDS = {
    "hoy": 0,
    "mañana": 1,
    "manana": 1,
    "pasado": 2,
    "semana": 7,
    "esta semana": 7,
}

STATS_KEYWORDS = ["racha", "record", "rendimiento", "estadistica", "acierto", "track"]

CONTEXT_KEYWORDS = [
    "y el de manana",
    "y manana",
    "y el otro",
    "ese equipo",
    "ese mismo",
    "el mismo",
    "que mas tiene",
    "otro partido",
    "siguiente",
    "proximo partido",
    "mas partidos",
    "mas informacion",
    "y el",
    "y la",
]

GREETING_WORDS = {
    "hola",
    "buenas",
    "buenos",
    "dias",
    "tardes",
    "noches",
    "como",
    "estas",
    "que",
    "tal",
    "hey",
    "hello",
    "hi",
    "gracias",
    "ayuda",
    "help",
    "oye",
    "saludos",
    "bien",
    "mal",
    "por",
    "favor",
}

DIVISION_NAMES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
    "EC": "Champions League",
    "WC": "FIFA World Cup",
}

RESULT_LABELS = {"H": "Local", "D": "Empate", "A": "Visitante"}

CONFIDENCE_EMOJI = {"alta": "🟢", "media": "🟡", "baja": "⚪"}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _resolve_team(token: str, known_teams: list[str]) -> str | None:
    normalized = _normalize(token)
    if normalized in TEAM_ALIASES:
        return TEAM_ALIASES[normalized]

    for name in known_teams:
        if _normalize(name) == normalized:
            return name

    for name in known_teams:
        if normalized in _normalize(name) or _normalize(name) in normalized:
            return name

    return None


def parse_query(text: str, known_teams: list[str], context: dict | None = None) -> dict:
    norm = _normalize(text)

    words = set(norm.split())
    if words and words.issubset(GREETING_WORDS):
        return {"intent": "greeting"}

    if context and context.get("last_team"):
        for kw in CONTEXT_KEYWORDS:
            if kw in norm:
                return {"intent": "team", "team": context["last_team"]}

    for kw in STATS_KEYWORDS:
        if kw in norm:
            return {"intent": "stats"}

    for kw in BEST_PICKS_KEYWORDS:
        if kw in norm:
            days_ahead = 7
            for date_kw, days in DATE_KEYWORDS.items():
                if date_kw in norm:
                    days_ahead = max(days, 1)
                    break
            return {"intent": "best_picks", "days_ahead": days_ahead}

    teams = []
    separators = re.split(r"\s+(?:vs\.?|contra|versus|[-–])\s+", text, maxsplit=1)

    if len(separators) == 2:
        t1 = _resolve_team(separators[0].strip(), known_teams)
        t2 = _resolve_team(separators[1].strip(), known_teams)
        if t1:
            teams.append(t1)
        if t2:
            teams.append(t2)
    else:
        for alias, canonical in sorted(TEAM_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
            if alias in norm:
                teams.append(canonical)
                norm = norm.replace(alias, "", 1)
                if len(teams) >= 2:
                    break

        if len(teams) < 2:
            for name in sorted(known_teams, key=len, reverse=True):
                if _normalize(name) in _normalize(text) and name not in teams:
                    teams.append(name)
                    if len(teams) >= 2:
                        break

    if len(teams) >= 2:
        return {"intent": "match", "team_a": teams[0], "team_b": teams[1]}
    if len(teams) == 1:
        return {"intent": "team", "team": teams[0]}

    return {"intent": "unknown"}


def handle_match(client, team_a: str, team_b: str) -> str:
    resp = (
        client.table("predictions")
        .select("*")
        .or_(
            f"and(home_team.eq.{team_a},away_team.eq.{team_b}),"
            f"and(home_team.eq.{team_b},away_team.eq.{team_a})"
        )
        .order("match_date", desc=True)
        .limit(1)
        .execute()
    )

    if resp.data:
        p = resp.data[0]
        return _format_prediction(p)

    resp2 = (
        client.table("matches")
        .select("*")
        .or_(
            f"and(home_team.eq.{team_a},away_team.eq.{team_b}),"
            f"and(home_team.eq.{team_b},away_team.eq.{team_a})"
        )
        .order("match_date", desc=True)
        .limit(1)
        .execute()
    )

    if resp2.data:
        m = resp2.data[0]
        if m.get("ft_result"):
            return _format_past_match(m)
        return (
            f"Tengo registrado **{m['home_team']} vs {m['away_team']}** "
            f"({m['match_date']}), pero aun no se ha generado una prediccion "
            f"para este partido. Las predicciones se actualizan diariamente."
        )

    on_demand = _predict_on_demand(team_a, team_b)
    if on_demand:
        return on_demand

    return (
        f"No encontre el partido **{team_a} vs {team_b}** en el sistema "
        f"y no tengo suficientes datos para generar una prediccion on-demand."
    )


def handle_team(client, team: str) -> str:
    today = date.today().isoformat()
    resp = (
        client.table("predictions")
        .select("*")
        .or_(f"home_team.eq.{team},away_team.eq.{team}")
        .gte("match_date", today)
        .order("match_date")
        .limit(5)
        .execute()
    )

    if resp.data:
        lines = [f"**Proximos partidos de {team}:**\n"]
        for p in resp.data:
            emoji = CONFIDENCE_EMOJI.get(p.get("confidence", ""), "")
            liga = DIVISION_NAMES.get(p["division"], p["division"])
            pred = RESULT_LABELS.get(p.get("predicted_result", ""), "?")
            lines.append(
                f"📅 **{p['match_date']}** — {p['home_team']} vs {p['away_team']} "
                f"({liga})\n"
                f"   Prediccion: **{pred}** {emoji} "
                f"| H: {p['prob_home']:.0%} D: {p['prob_draw']:.0%} "
                f"A: {p['prob_away']:.0%}"
            )
        return "\n\n".join(lines)

    resp2 = (
        client.table("matches")
        .select("match_date,home_team,away_team,division,ft_result,ft_home_goals,ft_away_goals")
        .or_(f"home_team.eq.{team},away_team.eq.{team}")
        .not_.is_("ft_result", "null")
        .order("match_date", desc=True)
        .limit(5)
        .execute()
    )

    if resp2.data:
        lines = [f"**Ultimos resultados de {team}:**\n"]
        for m in resp2.data:
            score = f"{m['ft_home_goals']}-{m['ft_away_goals']}"
            result = RESULT_LABELS.get(m["ft_result"], "?")
            lines.append(
                f"📅 {m['match_date']} — {m['home_team']} {score} {m['away_team']} → {result}"
            )
        return "\n\n".join(lines)

    return f"No encontre informacion sobre **{team}** en el sistema."


def handle_best_picks(client, days_ahead: int = 7) -> str:
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=days_ahead)).isoformat()

    resp = (
        client.table("predictions")
        .select("*")
        .gte("match_date", today)
        .lte("match_date", end)
        .eq("confidence", "alta")
        .order("match_date")
        .execute()
    )

    picks = resp.data or []

    if not picks:
        resp2 = (
            client.table("predictions")
            .select("*")
            .gte("match_date", today)
            .lte("match_date", end)
            .eq("confidence", "media")
            .order("match_date")
            .limit(5)
            .execute()
        )
        picks = resp2.data or []

    if not picks:
        return (
            "No hay predicciones de alta o media confianza disponibles "
            "en los proximos dias. Revisa mas tarde cuando se actualicen."
        )

    lines = ["**Mejores predicciones disponibles:**\n"]
    for p in picks[:8]:
        emoji = CONFIDENCE_EMOJI.get(p.get("confidence", ""), "")
        liga = DIVISION_NAMES.get(p["division"], p["division"])
        pred = RESULT_LABELS.get(p.get("predicted_result", ""), "?")
        max_prob = max(p["prob_home"], p["prob_draw"], p["prob_away"])
        lines.append(
            f"{emoji} **{p['home_team']} vs {p['away_team']}** — "
            f"{p['match_date']} ({liga})\n"
            f"   Prediccion: **{pred}** ({max_prob:.0%}) "
            f"| H: {p['prob_home']:.0%} D: {p['prob_draw']:.0%} "
            f"A: {p['prob_away']:.0%}"
        )

    lines.append(
        f"\n_Total: {len(picks)} predicciones de confianza {'alta' if resp.data else 'media'}_"
    )
    return "\n\n".join(lines)


def handle_stats(client) -> str:
    preds_resp = (
        client.table("predictions")
        .select("match_date,home_team,away_team,predicted_result,confidence")
        .order("match_date", desc=True)
        .limit(200)
        .execute()
    )
    if not preds_resp.data:
        return "No hay suficientes datos para mostrar estadisticas."

    pred_dates = list({p["match_date"] for p in preds_resp.data})
    pred_dates.sort()

    matches_resp = (
        client.table("matches")
        .select("match_date,home_team,away_team,ft_result")
        .not_.is_("ft_result", "null")
        .gte("match_date", pred_dates[0])
        .execute()
    )

    match_map = {}
    for m in matches_resp.data or []:
        match_map[(m["match_date"], m["home_team"], m["away_team"])] = m["ft_result"]

    total = 0
    hits = 0
    alta_total = 0
    alta_hits = 0

    for p in preds_resp.data:
        actual = match_map.get((p["match_date"], p["home_team"], p["away_team"]))
        if not actual:
            continue
        total += 1
        correct = p["predicted_result"] == actual
        if correct:
            hits += 1
        if p.get("confidence") == "alta":
            alta_total += 1
            if correct:
                alta_hits += 1

    if total == 0:
        return "Aun no hay predicciones resueltas para calcular estadisticas."

    hit_rate = hits / total
    alta_rate = alta_hits / alta_total if alta_total > 0 else 0

    return (
        f"**📊 Track Record del Modelo**\n\n"
        f"• Predicciones evaluadas: **{total}**\n"
        f"• Aciertos: **{hits}/{total}** ({hit_rate:.0%})\n"
        f"• Alta confianza: **{alta_hits}/{alta_total}** "
        f"({alta_rate:.0%})\n\n"
        f"_Las estadisticas se actualizan conforme se resuelven los partidos._"
    )


def handle_unknown() -> str:
    return (
        "No entendi tu consulta. Puedes preguntarme:\n\n"
        "• **Un partido**: _Argentina vs Algeria_\n"
        "• **Un equipo**: _Francia_\n"
        "• **Mejores picks**: _mejores apuestas de hoy_\n"
        "• **Track record**: _racha del modelo_"
    )


def _format_prediction(p: dict) -> str:
    liga = DIVISION_NAMES.get(p["division"], p["division"])
    pred = RESULT_LABELS.get(p.get("predicted_result", ""), "?")
    emoji = CONFIDENCE_EMOJI.get(p.get("confidence", ""), "")
    max_prob = max(p["prob_home"], p["prob_draw"], p["prob_away"])

    lines = [
        f"**{p['home_team']} vs {p['away_team']}**",
        f"📅 {p['match_date']} · {liga}\n",
        f"**Prediccion: {pred}** {emoji} Confianza: {p.get('confidence', '?')}\n",
        "| Resultado | Probabilidad |",
        "|-----------|-------------|",
        f"| Local (H) | **{p['prob_home']:.1%}** |",
        f"| Empate (D) | **{p['prob_draw']:.1%}** |",
        f"| Visitante (A) | **{p['prob_away']:.1%}** |",
    ]

    if p.get("prob_over25"):
        lines.append(f"\nOver 2.5 goles: **{p['prob_over25']:.1%}**")
    if p.get("prob_btts"):
        lines.append(f"Ambos anotan (BTTS): **{p['prob_btts']:.1%}**")

    if max_prob > 0.60:
        lines.append(
            f"\n💡 _El modelo tiene buena confianza en este resultado. "
            f"Probabilidad principal: {max_prob:.0%}_"
        )
    elif max_prob > 0.45:
        lines.append(
            f"\n⚖️ _Partido equilibrado. La probabilidad mas alta "
            f"es {max_prob:.0%} — considera el contexto._"
        )
    else:
        lines.append(
            "\n⚠️ _Partido muy parejo. Las probabilidades estan repartidas — precaucion al apostar._"
        )

    return "\n".join(lines)


def _format_past_match(m: dict) -> str:
    score = f"{m['ft_home_goals']}-{m['ft_away_goals']}"
    result = RESULT_LABELS.get(m["ft_result"], "?")
    liga = DIVISION_NAMES.get(m.get("division", ""), m.get("division", ""))

    return (
        f"**{m['home_team']} vs {m['away_team']}**\n"
        f"📅 {m['match_date']} · {liga}\n\n"
        f"Este partido ya se jugo. Resultado: **{score}** → **{result}**"
    )


def _predict_on_demand(home: str, away: str) -> str | None:
    """Try to generate a prediction using available features and the model."""
    try:
        from backend.etl.fixtures import load_national_features
        from backend.ml.config import FEATURES_PATH
        from backend.ml.predict import _model_cache, predict_upcoming
        from scripts.run_predictions import _build_feature_row_from_national

        national = load_national_features()
        if national and (home in national or away in national):
            feature_row = _build_feature_row_from_national(national, home, away, {})
            if feature_row:
                _model_cache.clear()
                feature_df = pd.DataFrame([feature_row])
                preds = predict_upcoming(feature_df, "WC")
                p = {
                    "home_team": home,
                    "away_team": away,
                    "match_date": "On-demand",
                    "division": "WC",
                    **preds,
                }
                header = "⚡ _Prediccion generada on-demand (no estaba en el sistema)_\n\n"
                return header + _format_prediction(p)

        if FEATURES_PATH.exists():
            tf = pd.read_parquet(FEATURES_PATH)
            tf["match_date"] = pd.to_datetime(tf["match_date"])
            home_feat = tf[tf["team"] == home].sort_values("match_date")
            away_feat = tf[tf["team"] == away].sort_values("match_date")

            if not home_feat.empty and not away_feat.empty:
                latest_home = home_feat.iloc[-1]
                latest_away = away_feat.iloc[-1]

                rolling_cols = [
                    "goals_scored_avg",
                    "goals_conceded_avg",
                    "shots_target_avg",
                    "corners_avg",
                    "win_rate",
                    "draw_rate",
                    "btts_rate",
                    "over25_rate",
                    "xg_for_avg",
                    "xg_against_avg",
                    "xg_diff_avg",
                    "xg_overperformance",
                    "goals_scored_avg_3",
                    "goals_conceded_avg_3",
                    "win_rate_3",
                    "goals_scored_avg_10",
                    "goals_conceded_avg_10",
                    "win_rate_10",
                    "venue_win_rate",
                    "venue_goals_avg",
                    "league_pos",
                    "h2h_win_rate",
                    "h2h_avg_goals",
                    "h2h_matches",
                ]
                feature_row = {}
                for col in rolling_cols:
                    feature_row[f"home_{col}"] = latest_home.get(col, float("nan"))
                    feature_row[f"away_{col}"] = latest_away.get(col, float("nan"))

                feature_row["home_elo"] = 1500.0
                feature_row["away_elo"] = 1500.0
                feature_row["elo_diff"] = 0.0
                feature_row["home_rest_days"] = 7
                feature_row["away_rest_days"] = 7
                feature_row["league_pos_diff"] = float("nan")

                division = latest_home.get("division", "E0")
                _model_cache.clear()
                feature_df = pd.DataFrame([feature_row])
                preds = predict_upcoming(feature_df, division)
                p = {
                    "home_team": home,
                    "away_team": away,
                    "match_date": "On-demand",
                    "division": division,
                    **preds,
                }
                header = "⚡ _Prediccion generada on-demand (no estaba en el sistema)_\n\n"
                return header + _format_prediction(p)

    except Exception as e:
        logger.warning("On-demand prediction failed: %s", e)

    return None


def get_response(
    client, text: str, known_teams: list[str], context: dict | None = None
) -> tuple[str, dict]:
    """Return (response_text, updated_context)."""
    query = parse_query(text, known_teams, context)
    ctx = dict(context) if context else {}

    if query["intent"] == "greeting":
        return (
            "👋 Hola! Preguntame sobre cualquier partido, equipo "
            "o las mejores apuestas disponibles.\n\n"
            "Ejemplos:\n"
            "• _Argentina vs Algeria_\n"
            "• _mejores picks_\n"
            "• _Francia_"
        ), ctx

    if query["intent"] == "match":
        ctx["last_team"] = query["team_a"]
        ctx["last_teams"] = [query["team_a"], query["team_b"]]
        return handle_match(client, query["team_a"], query["team_b"]), ctx

    if query["intent"] == "team":
        ctx["last_team"] = query["team"]
        return handle_team(client, query["team"]), ctx

    if query["intent"] == "best_picks":
        return handle_best_picks(client, query.get("days_ahead", 7)), ctx

    if query["intent"] == "stats":
        return handle_stats(client), ctx

    return handle_unknown(), ctx

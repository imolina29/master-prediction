"""Generate weekly performance report with Gemini AI narrative.

Runs Sunday at 11pm after the last results pipeline. Collects the
week's predictions vs results, calculates stats, and asks Gemini
to write a journalistic analysis. Stores the report in Supabase.

Usage:
    PYTHONPATH=. python scripts/run_weekly_report.py
"""

import json
import logging
import os
from datetime import date, timedelta

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

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


def _collect_week_stats(client, week_start: str, week_end: str) -> dict | None:
    """Gather predictions vs results for the given week."""
    preds_resp = (
        client.table("predictions")
        .select("*")
        .gte("match_date", week_start)
        .lte("match_date", week_end)
        .execute()
    )
    if not preds_resp.data:
        return None

    preds = pd.DataFrame(preds_resp.data)

    matches_resp = (
        client.table("matches")
        .select("match_date,home_team,away_team,division,ft_result,ft_home_goals,ft_away_goals")
        .not_.is_("ft_result", "null")
        .gte("match_date", week_start)
        .lte("match_date", week_end)
        .execute()
    )
    if not matches_resp.data:
        return None

    matches = pd.DataFrame(matches_resp.data)
    merged = preds.merge(
        matches[
            [
                "match_date",
                "home_team",
                "away_team",
                "ft_result",
                "ft_home_goals",
                "ft_away_goals",
            ]
        ],
        on=["match_date", "home_team", "away_team"],
        how="inner",
    )

    if merged.empty:
        return None

    merged["hit"] = merged["predicted_result"] == merged["ft_result"]
    total = len(merged)
    hits = int(merged["hit"].sum())
    rate = hits / total if total else 0

    # By confidence
    conf_stats = {}
    for conf in ["alta", "media", "baja"]:
        sub = merged[merged["confidence"] == conf]
        if not sub.empty:
            conf_stats[conf] = {
                "total": len(sub),
                "hits": int(sub["hit"].sum()),
                "rate": round(sub["hit"].mean(), 3),
            }

    # By league
    league_stats = {}
    for div in merged["division"].unique():
        sub = merged[merged["division"] == div]
        league_stats[DIVISION_NAMES.get(div, div)] = {
            "total": len(sub),
            "hits": int(sub["hit"].sum()),
            "rate": round(sub["hit"].mean(), 3),
        }

    # Draw analysis
    real_draws = int((merged["ft_result"] == "D").sum())
    pred_draws = int((merged["predicted_result"] == "D").sum())
    draw_misses = int(((merged["ft_result"] == "D") & (merged["predicted_result"] != "D")).sum())

    # Best hit (highest confidence correct prediction)
    hits_df = merged[merged["hit"]].copy()
    best_hit = None
    if not hits_df.empty:
        for conf in ["alta", "media", "baja"]:
            c = hits_df[hits_df["confidence"] == conf]
            if not c.empty:
                row = c.iloc[0]
                score = f"{int(row['ft_home_goals'])}-{int(row['ft_away_goals'])}"
                best_hit = {
                    "match": f"{row['home_team']} vs {row['away_team']}",
                    "score": score,
                    "prediction": RESULT_LABELS.get(row["predicted_result"], "?"),
                    "confidence": conf,
                    "league": DIVISION_NAMES.get(row["division"], row["division"]),
                }
                break

    # Worst miss (highest confidence wrong prediction)
    misses_df = merged[~merged["hit"]].copy()
    worst_miss = None
    if not misses_df.empty:
        for conf in ["alta", "media", "baja"]:
            c = misses_df[misses_df["confidence"] == conf]
            if not c.empty:
                row = c.iloc[0]
                score = f"{int(row['ft_home_goals'])}-{int(row['ft_away_goals'])}"
                worst_miss = {
                    "match": f"{row['home_team']} vs {row['away_team']}",
                    "score": score,
                    "prediction": RESULT_LABELS.get(row["predicted_result"], "?"),
                    "actual": RESULT_LABELS.get(row["ft_result"], "?"),
                    "confidence": conf,
                    "league": DIVISION_NAMES.get(row["division"], row["division"]),
                }
                break

    # Match details for Gemini
    match_details = []
    for _, r in merged.iterrows():
        score = f"{int(r['ft_home_goals'])}-{int(r['ft_away_goals'])}"
        match_details.append(
            {
                "match": f"{r['home_team']} vs {r['away_team']}",
                "league": DIVISION_NAMES.get(r["division"], r["division"]),
                "score": score,
                "prediction": RESULT_LABELS.get(r["predicted_result"], "?"),
                "actual": RESULT_LABELS.get(r["ft_result"], "?"),
                "confidence": r.get("confidence", "?"),
                "hit": bool(r["hit"]),
                "probs": {
                    "home": round(r.get("prob_home", 0) or 0, 2),
                    "draw": round(r.get("prob_draw", 0) or 0, 2),
                    "away": round(r.get("prob_away", 0) or 0, 2),
                },
            }
        )

    return {
        "week_start": week_start,
        "week_end": week_end,
        "total": total,
        "hits": hits,
        "rate": round(rate, 3),
        "by_confidence": conf_stats,
        "by_league": league_stats,
        "draws": {
            "real": real_draws,
            "predicted": pred_draws,
            "missed": draw_misses,
        },
        "best_hit": best_hit,
        "worst_miss": worst_miss,
        "matches": match_details,
    }


def _get_previous_week_rate(client, week_start: str) -> float | None:
    """Get last week's hit rate for comparison."""
    prev_end = (date.fromisoformat(week_start) - timedelta(days=1)).isoformat()
    prev_start = (date.fromisoformat(week_start) - timedelta(days=7)).isoformat()
    resp = (
        client.table("weekly_reports")
        .select("stats")
        .gte("week_start", prev_start)
        .lte("week_start", prev_end)
        .order("week_start", desc=True)
        .limit(1)
        .execute()
    )
    if resp.data and resp.data[0].get("stats"):
        stats = resp.data[0]["stats"]
        if isinstance(stats, str):
            stats = json.loads(stats)
        return stats.get("rate")
    return None


def _generate_narrative(stats: dict, prev_rate: float | None) -> str | None:
    """Ask Gemini to write a journalistic weekly report."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping narrative")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        comparison = ""
        if prev_rate is not None:
            diff = stats["rate"] - prev_rate
            direction = "subió" if diff > 0 else "bajó" if diff < 0 else "se mantuvo"
            comparison = (
                f"\nComparación: la semana pasada la precisión fue "
                f"{prev_rate:.1%}, esta semana {direction} a {stats['rate']:.1%}."
            )

        stats_summary = json.dumps(
            {k: v for k, v in stats.items() if k != "matches"},
            ensure_ascii=False,
            indent=2,
        )

        # Include top 5 most interesting matches
        interesting = sorted(
            stats["matches"],
            key=lambda m: (
                m["confidence"] == "alta",
                not m["hit"],
            ),
            reverse=True,
        )[:8]
        matches_text = json.dumps(interesting, ensure_ascii=False, indent=2)

        prompt = (
            f"Escribe una reseña semanal de rendimiento de Master Prediction "
            f"para la semana del {stats['week_start']} al {stats['week_end']}.\n\n"
            f"ESTADÍSTICAS:\n{stats_summary}\n"
            f"{comparison}\n\n"
            f"PARTIDOS DESTACADOS:\n{matches_text}\n\n"
            f"INSTRUCCIONES DE FORMATO:\n"
            f"- Escribe como un columnista deportivo profesional\n"
            f"- Empieza con un titular creativo (una línea, sin comillas)\n"
            f"- Después un párrafo de apertura enganchante\n"
            f"- Secciones: Lo Mejor, Lo Peor, Análisis por Liga, "
            f"Tendencias y Lecciones\n"
            f"- Usa datos concretos (porcentajes, marcadores)\n"
            f"- Máximo 500 palabras\n"
            f"- Tono: analítico pero apasionado, como una columna de "
            f"revista deportiva\n"
            f"- Usa **negritas** para destacar datos clave\n"
            f"- Termina con una frase de cierre memorable\n"
            f"- NO uses emojis ni hashtags\n"
            f"- NO inventes datos, usa SOLO los proporcionados"
        )

        system = (
            "Eres el editor deportivo de Master Prediction, una plataforma "
            "de inteligencia deportiva. Escribes reseñas semanales analizando "
            "el rendimiento del modelo de predicciones. Tu estilo es el de un "
            "columnista de revista deportiva: datos duros con narrativa "
            "envolvente. Nunca inventas estadísticas."
        )

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=4096,
                temperature=0.8,
            ),
        )

        return response.text if response.text else None

    except Exception as e:
        logger.warning("Gemini narrative generation failed: %s", e)
        return None


def main():
    from backend.db.client import get_supabase

    client = get_supabase()

    today = date.today()
    # Only generate on Sundays (or manual runs via --force)
    import sys

    force = "--force" in sys.argv
    if today.weekday() != 6 and not force:
        logger.info("Not Sunday (day=%d), skipping. Use --force to override.", today.weekday())
        return

    # Week = Monday to Sunday
    week_end = today.isoformat()
    week_start = (today - timedelta(days=6)).isoformat()

    logger.info("Generating weekly report for %s to %s", week_start, week_end)

    # Check if report already exists for this week
    existing = (
        client.table("weekly_reports")
        .select("id", count="exact")
        .eq("week_start", week_start)
        .execute()
    )
    if existing.count and existing.count > 0:
        logger.info("Report already exists for week %s, skipping", week_start)
        return

    stats = _collect_week_stats(client, week_start, week_end)
    if not stats:
        logger.info("No resolved predictions for week %s", week_start)
        return

    logger.info(
        "Week stats: %d/%d = %.1f%%",
        stats["hits"],
        stats["total"],
        stats["rate"] * 100,
    )

    prev_rate = _get_previous_week_rate(client, week_start)
    narrative = _generate_narrative(stats, prev_rate)

    if narrative:
        logger.info("Narrative generated (%d chars)", len(narrative))
    else:
        logger.warning("No narrative generated — storing stats only")

    # Store report
    row = {
        "week_start": week_start,
        "week_end": week_end,
        "total_predictions": stats["total"],
        "total_hits": stats["hits"],
        "hit_rate": stats["rate"],
        "stats": json.dumps(stats, ensure_ascii=False),
        "narrative": narrative,
    }
    client.table("weekly_reports").insert(row).execute()
    logger.info("Weekly report saved for %s", week_start)


if __name__ == "__main__":
    main()

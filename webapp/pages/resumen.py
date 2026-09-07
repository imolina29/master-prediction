"""Resumen Semanal — editorial-style weekly performance reports."""

import json
import re

from nicegui import ui

from webapp.theme import render_mini_strip

RESULT_LABELS = {"H": "Local", "D": "Empate", "A": "Visitante"}

LEAGUE_COLORS = {
    "Premier League": "#3d1d8e",
    "La Liga": "#e8590c",
    "Serie A": "#1b7d3a",
    "Bundesliga": "#d32f2f",
    "Ligue 1": "#0d5eaf",
    "Champions League": "#1b3c8c",
    "FIFA World Cup": "#7b1fa2",
}


def _md_to_html(text: str) -> str:
    """Convert markdown-style text to HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Split into headline + body
    lines = text.strip().split("\n", 1)
    headline = lines[0].strip().lstrip("#").strip()
    body = lines[1] if len(lines) > 1 else ""
    # Convert body paragraphs
    paragraphs = re.split(r"\n{2,}", body.strip())
    body_html = ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Check if it's a section header (## or ### prefix)
        if p.startswith("##"):
            header = p.lstrip("#").strip()
            body_html += f'<h3 class="wr-section">{header}</h3>'
        elif p.startswith("- ") or p.startswith("• "):
            items = p.split("\n")
            body_html += '<ul class="wr-list">'
            for item in items:
                item = item.lstrip("-•").strip()
                if item:
                    body_html += f"<li>{item}</li>"
            body_html += "</ul>"
        else:
            p = p.replace("\n", " ")
            body_html += f'<p class="wr-para">{p}</p>'
    return headline, body_html


def _stats_cards_html(stats: dict) -> str:
    """Render the stats summary cards."""
    rate_pct = round(stats.get("rate", 0) * 100)
    rate_color = (
        "var(--hit)" if rate_pct >= 55 else "var(--draw-color)" if rate_pct >= 40 else "var(--miss)"
    )

    conf = stats.get("by_confidence", {})
    alta = conf.get("alta", {})
    media = conf.get("media", {})

    draws = stats.get("draws", {})

    cards = (
        f'<div class="wr-stats">'
        f'<div class="wr-stat">'
        f'<div class="wr-stat-val" style="color:{rate_color}">{rate_pct}%</div>'
        f'<div class="wr-stat-lbl">Precision general</div>'
        f'<div class="wr-stat-sub">'
        f"{stats.get('hits', 0)}/{stats.get('total', 0)} aciertos</div>"
        f"</div>"
    )
    if alta:
        alta_pct = round(alta.get("rate", 0) * 100)
        cards += (
            f'<div class="wr-stat">'
            f'<div class="wr-stat-val" style="color:var(--hit)">{alta_pct}%</div>'
            f'<div class="wr-stat-lbl">Alta confianza</div>'
            f'<div class="wr-stat-sub">'
            f"{alta.get('hits', 0)}/{alta.get('total', 0)}</div>"
            f"</div>"
        )
    if media:
        media_pct = round(media.get("rate", 0) * 100)
        cards += (
            f'<div class="wr-stat">'
            f'<div class="wr-stat-val" style="color:var(--draw-color)">{media_pct}%</div>'
            f'<div class="wr-stat-lbl">Media confianza</div>'
            f'<div class="wr-stat-sub">'
            f"{media.get('hits', 0)}/{media.get('total', 0)}</div>"
            f"</div>"
        )
    cards += (
        f'<div class="wr-stat">'
        f'<div class="wr-stat-val" style="color:var(--miss)">'
        f"{draws.get('missed', 0)}</div>"
        f'<div class="wr-stat-lbl">Empates fallidos</div>'
        f'<div class="wr-stat-sub">'
        f"{draws.get('real', 0)} empates reales</div>"
        f"</div>"
    )
    cards += "</div>"
    return cards


def _league_bars_html(stats: dict) -> str:
    """Render league breakdown bars."""
    leagues = stats.get("by_league", {})
    if not leagues:
        return ""

    html = '<div class="wr-leagues"><h3 class="wr-section">Por liga</h3>'
    sorted_leagues = sorted(leagues.items(), key=lambda x: x[1].get("rate", 0), reverse=True)
    for name, data in sorted_leagues:
        pct = round(data.get("rate", 0) * 100)
        color = LEAGUE_COLORS.get(name, "var(--text-2)")
        pct_color = (
            "var(--hit)" if pct >= 55 else "var(--draw-color)" if pct >= 40 else "var(--miss)"
        )
        html += (
            f'<div class="wr-league-row">'
            f'<span class="wr-league-name" style="color:{color}">{name}</span>'
            f'<div class="wr-league-bar-bg">'
            f'<div class="wr-league-bar" style="width:{pct}%;background:{color}"></div>'
            f"</div>"
            f'<span class="wr-league-pct" style="color:{pct_color}">'
            f"{data.get('hits', 0)}/{data.get('total', 0)} ({pct}%)</span>"
            f"</div>"
        )
    html += "</div>"
    return html


def _highlights_html(stats: dict) -> str:
    """Render best hit and worst miss."""
    html = ""
    best = stats.get("best_hit")
    worst = stats.get("worst_miss")

    if best:
        html += (
            f'<div class="wr-highlight ok">'
            f'<div class="wr-hl-tag">Mejor acierto</div>'
            f'<div class="wr-hl-match">{best["match"]}</div>'
            f'<div class="wr-hl-detail">'
            f"{best['score']} · Pred: {best['prediction']} · "
            f"{best['confidence'].title()} · {best['league']}</div>"
            f"</div>"
        )
    if worst:
        html += (
            f'<div class="wr-highlight miss">'
            f'<div class="wr-hl-tag">Peor fallo</div>'
            f'<div class="wr-hl-match">{worst["match"]}</div>'
            f'<div class="wr-hl-detail">'
            f"{worst['score']} · Pred: {worst['prediction']} "
            f"(Real: {worst['actual']}) · "
            f"{worst['confidence'].title()} · {worst['league']}</div>"
            f"</div>"
        )
    return html


def render():
    render_mini_strip("Resumen Semanal", "Analisis editorial de rendimiento", "newspaper")

    from backend.db.client import get_supabase

    client = get_supabase()

    # Fetch all reports, newest first
    reports_resp = (
        client.table("weekly_reports")
        .select("*")
        .order("week_start", desc=True)
        .limit(12)
        .execute()
    )

    if not reports_resp.data:
        ui.html(
            '<div class="placeholder-box">'
            '<div class="ph-icon">📰</div>'
            '<div class="ph-title">Aun no hay resumenes semanales.</div>'
            '<div class="ph-sub">El primer reporte se genera automaticamente '
            "el domingo a las 11pm.</div>"
            "</div>"
        )
        return

    # Report selector if multiple
    reports = reports_resp.data
    options = {r["week_start"]: f"Semana {r['week_start']} al {r['week_end']}" for r in reports}

    if len(reports) > 1:
        selector = (
            ui.select(options, value=reports[0]["week_start"], label="Semana")
            .props('outlined dense dark color="orange-8"')
            .classes("w-72 mb-4")
        )
    else:
        selector = None

    report_container = ui.element("div").classes("w-full")

    def load_report(week_key=None):
        report_container.clear()
        key = week_key or reports[0]["week_start"]
        report = next((r for r in reports if r["week_start"] == key), reports[0])

        stats = report.get("stats")
        if isinstance(stats, str):
            stats = json.loads(stats)

        narrative = report.get("narrative", "")
        with report_container:
            # Header
            ui.html(
                f'<div class="wr-header">'
                f'<div class="wr-week">'
                f"Semana del {report['week_start']} al {report['week_end']}"
                f"</div>"
                f"</div>"
            )

            # Stats cards
            if stats:
                ui.html(_stats_cards_html(stats))

            # Narrative
            if narrative:
                headline, body_html = _md_to_html(narrative)
                ui.html(
                    f'<article class="wr-article">'
                    f'<h2 class="wr-headline">{headline}</h2>'
                    f"{body_html}"
                    f"</article>"
                )

            # Highlights
            if stats:
                ui.html(_highlights_html(stats))

            # League breakdown
            if stats:
                ui.html(_league_bars_html(stats))

    load_report()

    if selector:
        selector.on(
            "update:model-value",
            lambda e: load_report(e.args),
        )

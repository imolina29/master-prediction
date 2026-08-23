"""Predicciones — filterable predictions list + track record."""

from datetime import date, timedelta

from nicegui import ui

from webapp.data import DIVISION_NAMES, get_filtered_predictions, get_track_record
from webapp.theme import CHECK_SVG, CROSS_SVG, render_mini_strip

RESULT_LABELS = {"H": "Local", "D": "Empate", "A": "Visitante"}


def _pred_card_html(p: dict) -> str:
    league = DIVISION_NAMES.get(p.get("division", ""), p.get("division", ""))
    predicted = p.get("predicted_result", "H")
    pred_label = RESULT_LABELS.get(predicted, "?")
    confidence = p.get("confidence", "baja")
    conf_color = {"alta": "var(--hit)", "media": "var(--draw-color)", "baja": "var(--miss)"}.get(
        confidence, "var(--text-3)"
    )

    ph = p.get("prob_home", 0) or 0
    pd_ = p.get("prob_draw", 0) or 0
    pa = p.get("prob_away", 0) or 0
    hp, dp, ap = round(ph * 100), round(pd_ * 100), round(pa * 100)

    extras = []
    if p.get("prob_over25") is not None:
        extras.append(f"O2.5 {p['prob_over25']:.0%}")
    if p.get("prob_btts") is not None:
        extras.append(f"BTTS {p['prob_btts']:.0%}")
    extras_html = " · ".join(extras) if extras else ""

    return (
        f'<div class="pred-card">'
        f'<div class="pc-top">'
        f'<span class="pc-league">{league}</span>'
        f'<span class="pc-date">{p.get("match_date", "")}</span>'
        f"</div>"
        f'<div class="pc-teams">'
        f'<span class="pc-home">{p["home_team"]}</span>'
        f'<span class="pc-vs">vs</span>'
        f'<span class="pc-away">{p["away_team"]}</span>'
        f"</div>"
        f'<div class="force-track" style="height:22px;margin:8px 0 4px">'
        f'<div class="force-seg home" style="width:{hp}%">{hp}%</div>'
        f'<div class="force-seg draw" style="width:{dp}%">{dp}%</div>'
        f'<div class="force-seg away" style="width:{ap}%">{ap}%</div>'
        f"</div>"
        f'<div class="pc-bottom">'
        f'<span class="pc-pred">Pred: <strong>{pred_label}</strong></span>'
        f'<span class="pc-conf" style="color:{conf_color}">{confidence.title()}</span>'
        f'<span class="pc-extras">{extras_html}</span>'
        f"</div>"
        f"</div>"
    )


def render():
    render_mini_strip("Predicciones", "Modelo probabilistico", "clock")

    # Filters
    leagues = [("", "Todas las ligas")] + [(k, v) for k, v in DIVISION_NAMES.items()]
    confs = [("", "Todas"), ("alta", "Alta"), ("media", "Media"), ("baja", "Baja")]

    today = date.today()
    end = today + timedelta(days=21)

    with ui.row().classes("w-full items-end gap-4 mt-4 mb-4"):
        league_sel = (
            ui.select({k: v for k, v in leagues}, value="", label="Liga")
            .props('outlined dense dark color="orange-8"')
            .classes("w-48")
        )

        conf_sel = (
            ui.select({k: v for k, v in confs}, value="", label="Confianza")
            .props('outlined dense dark color="orange-8"')
            .classes("w-36")
        )

        date_from = (
            ui.input("Desde", value=today.isoformat())
            .props('outlined dense dark color="orange-8" type="date"')
            .classes("w-40")
        )

        date_to = (
            ui.input("Hasta", value=end.isoformat())
            .props('outlined dense dark color="orange-8" type="date"')
            .classes("w-40")
        )

    preds_container = ui.element("div").classes("w-full")
    track_container = ui.element("div").classes("w-full mt-6")

    def load_data():
        preds_container.clear()
        track_container.clear()

        div = league_sel.value or None
        conf = conf_sel.value or None
        df_from = date_from.value or None
        df_to = date_to.value or None

        try:
            preds_df = get_filtered_predictions(div, conf, df_from, df_to)
        except Exception:
            preds_df = None

        with preds_container:
            if preds_df is not None and not preds_df.empty:
                alta = (
                    len(preds_df[preds_df["confidence"] == "alta"])
                    if "confidence" in preds_df.columns
                    else 0
                )
                media = (
                    len(preds_df[preds_df["confidence"] == "media"])
                    if "confidence" in preds_df.columns
                    else 0
                )
                baja = (
                    len(preds_df[preds_df["confidence"] == "baja"])
                    if "confidence" in preds_df.columns
                    else 0
                )

                ui.html(
                    f'<div class="kpi-row">'
                    f'<div class="kpi"><div class="kpi-val">{len(preds_df)}</div><div class="kpi-lbl">Total</div></div>'
                    f'<div class="kpi"><div class="kpi-val" style="color:var(--hit)">{alta}</div><div class="kpi-lbl">Alta</div></div>'
                    f'<div class="kpi"><div class="kpi-val" style="color:var(--draw-color)">{media}</div><div class="kpi-lbl">Media</div></div>'
                    f'<div class="kpi"><div class="kpi-val" style="color:var(--miss)">{baja}</div><div class="kpi-lbl">Baja</div></div>'
                    f"</div>"
                )

                cards_html = '<div class="pred-grid">'
                for _, p in preds_df.iterrows():
                    cards_html += _pred_card_html(p.to_dict())
                cards_html += "</div>"
                ui.html(cards_html)
            else:
                ui.html(
                    '<div class="placeholder-box">'
                    '<div class="ph-icon">📭</div>'
                    '<div class="ph-title">No hay predicciones para el rango seleccionado.</div>'
                    "</div>"
                )

        # Track record
        try:
            track = get_track_record(limit=100)
        except Exception:
            track = None

        with track_container:
            if track is not None and not track.empty:
                track["hit"] = track["predicted_result"] == track["ft_result"]
                total = len(track)
                hits = int(track["hit"].sum())
                rate = hits / total if total else 0

                ui.html(
                    f'<div class="track-panel">'
                    f'<div class="tp-head"><h2>Track Record ({hits}/{total} — {rate:.0%})</h2></div>'
                )

                rows_html = ""
                for _, row in track.head(20).iterrows():
                    hit = row["predicted_result"] == row["ft_result"]
                    score = f"{int(row['ft_home_goals'])}–{int(row['ft_away_goals'])}"
                    pred = RESULT_LABELS.get(row["predicted_result"], "?")
                    check_cls = "ok" if hit else "no"
                    check_icon = CHECK_SVG if hit else CROSS_SVG
                    d = str(row["match_date"])
                    if len(d) > 5:
                        d = d[5:]
                    rows_html += (
                        f'<div class="tp-row">'
                        f'<span class="tp-date">{d}</span>'
                        f'<span class="tp-match">{row["home_team"]} vs {row["away_team"]}</span>'
                        f'<span class="tp-score">{score}</span>'
                        f'<span class="tp-pred">{pred}</span>'
                        f'<span class="tp-icon"><span class="tp-check {check_cls}">{check_icon}</span></span>'
                        f"</div>"
                    )
                ui.html(rows_html + "</div>")

    load_data()

    for el in [league_sel, conf_sel, date_from, date_to]:
        el.on("update:model-value", lambda: load_data())

"""Home — broadcast-style sports analytics dashboard."""

from nicegui import ui

from webapp.data import DIVISION_NAMES, get_track_record, get_upcoming_predictions
from webapp.theme import CHECK_SVG, CROSS_SVG, DONUT_JS, SPARK_JS, render_hero_banner

RESULT_LABELS = {"H": "Local", "D": "Empate", "A": "Visitante"}

LEAGUE_COLORS = {
    "E0": "var(--info)",
    "SP1": "var(--flame)",
    "I1": "var(--hit)",
    "D1": "var(--draw-color)",
    "F1": "var(--miss)",
    "EC": "var(--text-2)",
    "WC": "var(--flame)",
}


def _force_bar_html(h: float, d: float, a: float, size: str = "big") -> str:
    hp, dp, ap = round(h * 100), round(d * 100), round(a * 100)
    if size == "big":
        return (
            f'<div class="force-track">'
            f'<div class="force-seg home" style="width:{hp}%">{hp}%</div>'
            f'<div class="force-seg draw" style="width:{dp}%">{dp}%</div>'
            f'<div class="force-seg away" style="width:{ap}%">{ap}%</div>'
            f"</div>"
        )
    return (
        f'<div class="ml-force-track">'
        f'<div class="ml-force-seg home" style="width:{hp}%">{hp}</div>'
        f'<div class="ml-force-seg draw" style="width:{dp}%">{dp}</div>'
        f'<div class="ml-force-seg away" style="width:{ap}%">{ap}</div>'
        f"</div>"
    )


def _featured_match_html(p: dict) -> str:
    league = DIVISION_NAMES.get(p.get("division", ""), p.get("division", ""))
    div = p.get("division", "")
    predicted = p.get("predicted_result", "H")
    confidence = p.get("confidence", "media")
    pred_label = RESULT_LABELS.get(predicted, "?")

    conf_color = {"alta": "var(--hit)", "media": "var(--draw-color)", "baja": "var(--miss)"}.get(
        confidence, "var(--text-3)"
    )
    force = _force_bar_html(
        p.get("prob_home", 0.33), p.get("prob_draw", 0.33), p.get("prob_away", 0.34), size="big"
    )

    pick_labels = {
        "H": '<span class="pick">▸ Local</span><span>Empate</span><span>Visitante</span>',
        "D": '<span>Local</span><span class="pick">▸ Empate</span><span>Visitante</span>',
        "A": '<span>Local</span><span>Empate</span><span class="pick">▸ Visitante</span>',
    }

    extras = []
    if p.get("prob_over25") is not None:
        extras.append(f"Over 2.5: <strong>{p['prob_over25']:.0%}</strong>")
    if p.get("prob_btts") is not None:
        extras.append(f"BTTS: <strong>{p['prob_btts']:.0%}</strong>")
    extras.append(f'Confianza: <strong style="color:{conf_color}">{confidence.title()}</strong>')
    extras_html = "".join(f"<span>{e}</span>" for e in extras)

    return (
        f'<div class="featured">'
        f'<div class="f-stripe"></div>'
        f'<div class="f-label">'
        f'<span class="f-tag">Prediccion destacada</span>'
        f'<span class="f-league">{div} · {league}</span>'
        f"</div>"
        f'<div class="f-body">'
        f'<div class="f-team"><div class="f-team-name">{p["home_team"]}</div>'
        f'<div class="f-team-sub">Pred: {pred_label}</div></div>'
        f'<div class="f-vs"><div class="f-vs-label">vs</div>'
        f'<div class="f-vs-date">{p["match_date"]}</div></div>'
        f'<div class="f-team away"><div class="f-team-name">{p["away_team"]}</div>'
        f'<div class="f-team-sub">&nbsp;</div></div>'
        f"</div>"
        f'<div class="force-bar">{force}'
        f'<div class="force-labels">{pick_labels.get(predicted, pick_labels["H"])}</div>'
        f"</div>"
        f'<div class="f-extras">{extras_html}</div>'
        f"</div>"
    )


def _match_row_html(p: dict) -> str:
    league = DIVISION_NAMES.get(p.get("division", ""), p.get("division", ""))
    div = p.get("division", "")
    confidence = p.get("confidence", "baja")
    predicted = p.get("predicted_result", "?")
    pred_label = RESULT_LABELS.get(predicted, "?")
    dot_color = LEAGUE_COLORS.get(div, "var(--text-3)")
    force = _force_bar_html(
        p.get("prob_home", 0.33), p.get("prob_draw", 0.33), p.get("prob_away", 0.34), size="small"
    )
    return (
        f'<div class="ml-row">'
        f'<div class="ml-conf {confidence}"></div>'
        f'<div class="ml-info">'
        f'<div class="ml-teams">{p["home_team"]} vs {p["away_team"]}</div>'
        f'<div class="ml-meta"><span class="league-dot" style="background:{dot_color}"></span> {league} · {p["match_date"]}</div>'
        f"</div>"
        f'<div class="ml-force">{force}'
        f'<div class="ml-pred">Pred: <strong>{pred_label}</strong></div>'
        f"</div></div>"
    )


def render():
    try:
        preds_df = get_upcoming_predictions()
    except Exception:
        preds_df = None

    try:
        track = get_track_record(limit=200)
    except Exception:
        track = None

    # Compute track record stats for hero banner
    total_resolved = total_hits = 0
    hit_rate = 0.0
    alta_hits = alta_total = 0
    alta_rate = 0.0
    if track is not None and not track.empty:
        track["hit"] = track["predicted_result"] == track["ft_result"]
        total_resolved = len(track)
        total_hits = int(track["hit"].sum())
        hit_rate = total_hits / total_resolved if total_resolved else 0
        ht = track[track["confidence"] == "alta"]
        if not ht.empty:
            alta_hits = int(ht["hit"].sum())
            alta_total = len(ht)
            alta_rate = alta_hits / alta_total

    render_hero_banner(
        {
            "matches": total_resolved,
            "hit_rate": hit_rate,
            "leagues": 6,
        }
    )

    # Featured match
    if preds_df is not None and not preds_df.empty:
        alta = (
            preds_df[preds_df.get("confidence", "") == "alta"]
            if "confidence" in preds_df.columns
            else preds_df
        )
        featured = alta.iloc[0].to_dict() if not alta.empty else preds_df.iloc[0].to_dict()
        ui.html(_featured_match_html(featured))

        remaining = preds_df[
            ~(
                (preds_df["home_team"] == featured["home_team"])
                & (preds_df["away_team"] == featured["away_team"])
            )
        ]
    else:
        remaining = None

    # Grid: matches + right col
    with ui.element("div").classes("mp-grid"):
        # LEFT: match list
        with ui.element("div"):
            total_preds = len(remaining) if remaining is not None and not remaining.empty else 0
            rows_html = (
                f'<div class="match-list">'
                f'<div class="ml-head"><h2>Proximas predicciones</h2>'
                f'<span class="count">{total_preds} partidos</span></div>'
            )
            if remaining is not None and not remaining.empty:
                for _, p in remaining.head(8).iterrows():
                    rows_html += _match_row_html(p.to_dict())
            else:
                rows_html += (
                    '<div style="padding:24px;text-align:center;color:var(--text-3);font-size:13px">'
                    "No hay mas predicciones disponibles.</div>"
                )
            rows_html += "</div>"
            ui.html(rows_html)

        # RIGHT: donut + sparkline + leagues
        with ui.element("div").style("display:flex;flex-direction:column;gap:16px"):
            # Donut
            donut_html = (
                f'<div class="donut-panel">'
                f"<h3>Precision del modelo</h3>"
                f'<div class="donut-wrap">'
                f'<canvas id="donut-chart" width="100" height="100" data-hit="{hit_rate:.2f}"></canvas>'
                f'<div class="donut-stats">'
                f'<div class="donut-stat"><span class="ds-label"><span class="ds-dot" style="background:var(--hit)"></span> Aciertos</span><span class="ds-val">{total_hits}</span></div>'
                f'<div class="donut-stat"><span class="ds-label"><span class="ds-dot" style="background:var(--miss)"></span> Fallos</span><span class="ds-val">{total_resolved - total_hits}</span></div>'
                f'<div class="donut-stat"><span class="ds-label"><span class="ds-dot" style="background:var(--edge)"></span> Total</span><span class="ds-val">{total_resolved}</span></div>'
                f"</div></div></div>"
            )
            ui.html(donut_html)
            ui.run_javascript(DONUT_JS)

            # Sparkline
            spark_points = ""
            if track is not None and not track.empty:
                window = 10
                hits_list = track["hit"].astype(int).tolist()[::-1]
                rolling = []
                for i in range(len(hits_list)):
                    chunk = hits_list[max(0, i - window + 1) : i + 1]
                    rolling.append(round(sum(chunk) / len(chunk) * 100))
                if len(rolling) > 20:
                    rolling = rolling[-20:]
                spark_points = ",".join(str(v) for v in rolling)

            spark_html = (
                f'<div class="spark-panel">'
                f"<h3>Alta confianza</h3>"
                f'<div class="sp-sub">Precision ultimas predicciones alta conf.</div>'
                f'<div class="spark-big">{round(alta_rate * 100)}<span class="unit">%</span></div>'
                f'<div style="font-size:11px;color:var(--text-3);margin-bottom:10px">{alta_hits}/{alta_total} acertadas</div>'
                f'<canvas id="spark-chart" width="280" height="60" data-points="{spark_points}"></canvas>'
                f"</div>"
            )
            ui.html(spark_html)
            ui.run_javascript(SPARK_JS)

            # Leagues breakdown
            if track is not None and not track.empty:
                by_div = track.groupby("division")["hit"].agg(["sum", "count"])
                if not by_div.empty:
                    lp_html = (
                        '<div class="leagues-panel"><div class="ml-head"><h2>Por liga</h2></div>'
                    )
                    for div_code in by_div.index:
                        hits = int(by_div.loc[div_code, "sum"])
                        total = int(by_div.loc[div_code, "count"])
                        rate = hits / total if total else 0
                        pct_color = (
                            "var(--hit)"
                            if rate >= 0.55
                            else "var(--draw-color)"
                            if rate >= 0.40
                            else "var(--miss)"
                        )
                        name = DIVISION_NAMES.get(div_code, div_code)
                        lc = LEAGUE_COLORS.get(div_code, "var(--text-2)")
                        lp_html += (
                            f'<div class="lp-row">'
                            f'<span class="lp-name" style="color:{lc}">{name}</span>'
                            f'<span class="lp-record">{hits}/{total}</span>'
                            f'<span class="lp-pct" style="color:{pct_color}">{rate:.0%}</span>'
                            f"</div>"
                        )
                    lp_html += "</div>"
                    ui.html(lp_html)

    # Track record
    if track is not None and not track.empty:
        recent = track.head(10)
        streak_html = '<div class="streak">'
        for _, row in recent.iterrows():
            hit = row["predicted_result"] == row["ft_result"]
            cls = "w" if hit else "l"
            lbl = "W" if hit else "L"
            streak_html += f'<div class="dot {cls}">{lbl}</div>'
        streak_html += "</div>"

        tp_html = (
            f'<div class="track-panel">'
            f'<div class="tp-head"><h2>Ultimos resultados</h2>{streak_html}</div>'
        )
        for _, row in recent.iterrows():
            hit = row["predicted_result"] == row["ft_result"]
            score = f"{int(row['ft_home_goals'])}–{int(row['ft_away_goals'])}"
            pred = RESULT_LABELS.get(row["predicted_result"], "?")
            check_cls = "ok" if hit else "no"
            check_icon = CHECK_SVG if hit else CROSS_SVG
            date_str = str(row["match_date"])
            if len(date_str) > 5:
                date_str = date_str[5:]
            tp_html += (
                f'<div class="tp-row">'
                f'<span class="tp-date">{date_str}</span>'
                f'<span class="tp-match">{row["home_team"]} vs {row["away_team"]}</span>'
                f'<span class="tp-score">{score}</span>'
                f'<span class="tp-pred">{pred}</span>'
                f'<span class="tp-icon"><span class="tp-check {check_cls}">{check_icon}</span></span>'
                f"</div>"
            )
        tp_html += "</div>"
        ui.html(tp_html)

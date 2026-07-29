"""Calibration — backtest metrics and model comparison."""

import json
from pathlib import Path

from nicegui import ui

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKTEST_PATH = _PROJECT_ROOT / "data" / "backtest_results.json"


def _load_results() -> dict:
    try:
        from webapp.data import get_supabase_client

        client = get_supabase_client()
        resp = client.table("backtest_results").select("*").execute()
        if resp.data:
            return {row["id"]: row["results"] for row in resp.data}
    except Exception:
        pass
    if not BACKTEST_PATH.exists():
        return {}
    with open(BACKTEST_PATH) as f:
        return json.load(f)


def render():
    from webapp.theme import render_mini_strip

    render_mini_strip("Calibracion del Modelo", "Rendimiento", "target")

    results = _load_results()
    if not results:
        ui.html(
            '<div class="placeholder-box">'
            '<div class="ph-icon">📊</div>'
            '<div class="ph-title">No hay resultados de backtesting disponibles.</div>'
            '<div class="ph-sub">Ejecuta el entrenamiento primero.</div>'
            "</div>"
        )
        return

    best_acc = max((d.get("mean_accuracy", 0) for d in results.values()), default=0)
    best_model = max(results, key=lambda k: results[k].get("mean_accuracy", 0))
    roi_vals = [d["mean_roi_pct"] for d in results.values() if "mean_roi_pct" in d]
    best_roi = max(roi_vals) if roi_vals else 0
    total_folds = sum(len(d.get("folds", [])) for d in results.values())

    ui.html(
        f'<div class="kpi-row">'
        f'<div class="kpi"><div class="kpi-val" style="color:var(--hit)">{best_acc:.1%}</div>'
        f'<div class="kpi-lbl">Mejor Accuracy</div></div>'
        f'<div class="kpi"><div class="kpi-val">{best_roi:.1f}%</div>'
        f'<div class="kpi-lbl">Mejor ROI</div></div>'
        f'<div class="kpi"><div class="kpi-val">{best_model}</div>'
        f'<div class="kpi-lbl">Mejor Modelo</div></div>'
        f'<div class="kpi"><div class="kpi-val">{total_folds}</div>'
        f'<div class="kpi-lbl">Folds evaluados</div></div>'
        f"</div>"
    )

    # Summary table
    table_html = (
        '<div class="standings-panel">'
        '<div class="ml-head"><h2>Comparacion de Modelos</h2></div>'
        '<div class="st-table" style="min-width:500px">'
        '<div class="st-header" style="grid-template-columns:1fr repeat(4, 80px)">'
        '<span class="st-team">Modelo</span>'
        '<span class="st-num">Accuracy</span>'
        '<span class="st-num">Log Loss</span>'
        '<span class="st-num">Brier</span>'
        '<span class="st-num">ROI</span>'
        "</div>"
    )

    for name, data in sorted(results.items(), key=lambda x: -x[1].get("mean_accuracy", 0)):
        acc = data.get("mean_accuracy", 0)
        ll = data.get("mean_log_loss", 0)
        brier = data.get("mean_brier_score", 0)
        roi = data.get("mean_roi_pct", 0)
        is_best = name == best_model
        highlight = "border-left:3px solid var(--flame);" if is_best else ""

        table_html += (
            f'<div class="st-row" style="grid-template-columns:1fr repeat(4, 80px);{highlight}">'
            f'<span class="st-team">{name}</span>'
            f'<span class="st-num st-pts">{acc:.1%}</span>'
            f'<span class="st-num">{ll:.4f}</span>'
            f'<span class="st-num">{brier:.4f}</span>'
            f'<span class="st-num">{roi:.1f}%</span>'
            f"</div>"
        )

    table_html += "</div></div>"
    ui.html(table_html)

    # Detail by season per model
    model_names = sorted(results.keys())
    model_sel = (
        ui.select({m: m for m in model_names}, value=model_names[0], label="Detalle por temporada")
        .props('outlined dense dark color="orange-8"')
        .classes("w-52 mt-4")
    )

    detail_container = ui.element("div").classes("w-full mt-2")

    def show_detail():
        detail_container.clear()
        name = model_sel.value
        if not name or name not in results:
            return
        data = results[name]
        folds = data.get("folds", [])
        if not folds:
            return

        with detail_container:
            d_html = (
                '<div class="standings-panel">'
                '<div class="ml-head"><h2>Temporadas — ' + name + "</h2></div>"
                '<div class="st-table" style="min-width:400px">'
                '<div class="st-header" style="grid-template-columns:1fr repeat(3, 80px)">'
                '<span class="st-team">Temporada</span>'
                '<span class="st-num">Accuracy</span>'
                '<span class="st-num">Log Loss</span>'
                '<span class="st-num">Muestras</span>'
                "</div>"
            )
            for fold in folds:
                season = fold.get("season", fold.get("fold", "—"))
                acc = fold.get("accuracy", 0)
                ll = fold.get("log_loss", 0)
                n = fold.get("n_test", 0)
                d_html += (
                    f'<div class="st-row" style="grid-template-columns:1fr repeat(3, 80px)">'
                    f'<span class="st-team">{season}</span>'
                    f'<span class="st-num">{acc:.1%}</span>'
                    f'<span class="st-num">{ll:.4f}</span>'
                    f'<span class="st-num">{n}</span>'
                    f"</div>"
                )
            mean_acc = data.get("mean_accuracy", 0)
            mean_ll = data.get("mean_log_loss", 0)
            d_html += "</div></div>"
            d_html += (
                f'<div style="font-size:11px;color:var(--text-3);margin-top:8px">'
                f"Promedio — Accuracy: {mean_acc:.1%} | Log Loss: {mean_ll:.4f}</div>"
            )
            ui.html(d_html)

    model_sel.on("update:model-value", lambda: show_detail())
    show_detail()

    # Interpretation guide
    with (
        ui.expansion("Guia de interpretacion")
        .classes("mt-4")
        .style("background:var(--surface);border:1px solid var(--edge);border-radius:var(--radius)")
    ):
        ui.html(
            '<div style="font-size:12px;color:var(--text-2);line-height:1.8;padding:8px">'
            "<strong>Accuracy:</strong> % predicciones correctas. Mayor = mejor.<br>"
            "<strong>Log Loss:</strong> Calidad de probabilidades. Menor = mejor (0 = perfecto).<br>"
            "<strong>Brier Score:</strong> Error cuadratico de probabilidades. Menor = mejor.<br>"
            "<strong>ROI:</strong> Retorno simulado apostando cuando el modelo detecta ventaja (&gt;5% edge).<br>"
            "<strong>Calibracion perfecta:</strong> Cuando el modelo dice 60%, ocurre 60% de las veces."
            "</div>"
        )

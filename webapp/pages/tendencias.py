"""Tendencias — performance trends and analytics."""

from nicegui import ui

from webapp.data import DIVISION_NAMES, get_supabase_client
from webapp.theme import render_mini_strip


def _load_resolved() -> list[dict]:
    try:
        client = get_supabase_client()
        resp = (
            client.table("value_bets")
            .select("*")
            .not_.is_("result", "null")
            .order("match_date", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


def render():
    render_mini_strip("Tendencias", "Rendimiento", "pulse")

    resolved = _load_resolved()
    if not resolved:
        ui.html(
            '<div class="placeholder-box">'
            '<div class="ph-icon">📈</div>'
            '<div class="ph-title">No hay suficientes datos para analizar tendencias.</div>'
            '<div class="ph-sub">Las tendencias se generan a medida que los picks se resuelven.</div>'
            "</div>"
        )
        return

    try:
        import os

        import httpx

        api_url = os.environ.get("BACKEND_API_URL", "http://localhost:8081")
        api_key = os.environ.get("API_KEY_WEBAPP", "")
        resp = httpx.post(
            f"{api_url}/api/performance",
            json={"resolved_picks": resolved},
            headers={"X-API-Key": api_key},
            timeout=15.0,
        )
        resp.raise_for_status()
        perf = resp.json()
    except Exception:
        perf = {
            "total_picks": len(resolved),
            "wins": sum(1 for r in resolved if r.get("result") == "win"),
            "losses": sum(1 for r in resolved if r.get("result") == "loss"),
            "profit": 0,
            "roi": 0,
            "hit_rate": 0,
            "by_market": {},
        }
        if perf["total_picks"]:
            perf["hit_rate"] = perf["wins"] / perf["total_picks"]

    profit_sign = "+" if perf.get("profit", 0) >= 0 else ""
    profit_color = "var(--hit)" if perf.get("profit", 0) >= 0 else "var(--miss)"

    ui.html(
        f'<div class="kpi-row">'
        f'<div class="kpi"><div class="kpi-val">{perf["total_picks"]}</div>'
        f'<div class="kpi-lbl">Total picks resueltos</div></div>'
        f'<div class="kpi"><div class="kpi-val" style="color:{profit_color}">'
        f"{profit_sign}{perf.get('profit', 0):.1f}u</div>"
        f'<div class="kpi-lbl">Profit acumulado</div></div>'
        f'<div class="kpi"><div class="kpi-val">{perf.get("roi", 0):.1f}%</div>'
        f'<div class="kpi-lbl">ROI global</div></div>'
        f'<div class="kpi"><div class="kpi-val" style="color:var(--hit)">{perf.get("hit_rate", 0):.0%}</div>'
        f'<div class="kpi-lbl">{perf.get("wins", 0)} ganados</div></div>'
        f"</div>"
    )

    # Profit evolution (simple text-based sparkline)
    running_profit = 0.0
    timeline_points = []
    for pick in reversed(resolved):
        pl = pick.get("profit_loss", 0) or 0
        running_profit += pl
        timeline_points.append(round(running_profit, 2))

    if timeline_points:
        spark_data = ",".join(str(int(p * 10)) for p in timeline_points[-30:])
        ui.html(
            f'<div class="spark-panel">'
            f"<h3>Evolucion del Profit</h3>"
            f'<div class="sp-sub">Ultimos {min(30, len(timeline_points))} picks resueltos</div>'
            f'<canvas id="spark-chart" width="600" height="80" data-points="{spark_data}"></canvas>'
            f"</div>"
        )
        from webapp.theme import SPARK_JS

        ui.run_javascript(SPARK_JS)

    # By league
    by_league: dict[str, dict] = {}
    for pick in resolved:
        div = pick.get("division", "?")
        if div not in by_league:
            by_league[div] = {"wins": 0, "total": 0, "profit": 0.0}
        by_league[div]["total"] += 1
        if pick.get("result") == "win":
            by_league[div]["wins"] += 1
        by_league[div]["profit"] += pick.get("profit_loss", 0) or 0

    if by_league:
        t_html = (
            '<div class="standings-panel" style="margin-top:16px">'
            '<div class="ml-head"><h2>Rendimiento por Liga</h2></div>'
            '<div class="st-table" style="min-width:400px">'
            '<div class="st-header" style="grid-template-columns:1fr repeat(3, 80px)">'
            '<span class="st-team">Liga</span>'
            '<span class="st-num">Acierto</span>'
            '<span class="st-num">Picks</span>'
            '<span class="st-num">Profit</span>'
            "</div>"
        )
        for div in sorted(by_league, key=lambda d: -by_league[d]["total"]):
            info = by_league[div]
            rate = info["wins"] / info["total"] if info["total"] else 0
            name = DIVISION_NAMES.get(div, div)
            rate_color = (
                "var(--hit)"
                if rate >= 0.55
                else "var(--draw-color)"
                if rate >= 0.40
                else "var(--miss)"
            )
            p_sign = "+" if info["profit"] >= 0 else ""
            p_color = "var(--hit)" if info["profit"] >= 0 else "var(--miss)"

            t_html += (
                f'<div class="st-row" style="grid-template-columns:1fr repeat(3, 80px)">'
                f'<span class="st-team">{name}</span>'
                f'<span class="st-num" style="color:{rate_color}">{rate:.0%}</span>'
                f'<span class="st-num">{info["total"]}</span>'
                f'<span class="st-num" style="color:{p_color}">{p_sign}{info["profit"]:.1f}u</span>'
                f"</div>"
            )
        t_html += "</div></div>"
        ui.html(t_html)

    # By market/stake
    by_market: dict[str, dict] = {}
    for pick in resolved:
        mkt = pick.get("market", "1X2")
        if mkt not in by_market:
            by_market[mkt] = {"wins": 0, "total": 0, "profit": 0.0}
        by_market[mkt]["total"] += 1
        if pick.get("result") == "win":
            by_market[mkt]["wins"] += 1
        by_market[mkt]["profit"] += pick.get("profit_loss", 0) or 0

    if by_market:
        m_html = (
            '<div class="standings-panel" style="margin-top:16px">'
            '<div class="ml-head"><h2>Rendimiento por Mercado</h2></div>'
            '<div class="st-table" style="min-width:400px">'
            '<div class="st-header" style="grid-template-columns:1fr repeat(3, 80px)">'
            '<span class="st-team">Mercado</span>'
            '<span class="st-num">Acierto</span>'
            '<span class="st-num">Picks</span>'
            '<span class="st-num">Profit</span>'
            "</div>"
        )
        for mkt in sorted(by_market, key=lambda m: -by_market[m]["total"]):
            info = by_market[mkt]
            rate = info["wins"] / info["total"] if info["total"] else 0
            rate_color = (
                "var(--hit)"
                if rate >= 0.55
                else "var(--draw-color)"
                if rate >= 0.40
                else "var(--miss)"
            )
            p_sign = "+" if info["profit"] >= 0 else ""
            p_color = "var(--hit)" if info["profit"] >= 0 else "var(--miss)"

            m_html += (
                f'<div class="st-row" style="grid-template-columns:1fr repeat(3, 80px)">'
                f'<span class="st-team">{mkt}</span>'
                f'<span class="st-num" style="color:{rate_color}">{rate:.0%}</span>'
                f'<span class="st-num">{info["total"]}</span>'
                f'<span class="st-num" style="color:{p_color}">{p_sign}{info["profit"]:.1f}u</span>'
                f"</div>"
            )
        m_html += "</div></div>"
        ui.html(m_html)

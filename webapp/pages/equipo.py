"""Team Analysis — per-team stats, record, and last results."""

from nicegui import ui

from webapp.data import DIVISION_NAMES, get_seasons, get_teams, load_matches
from webapp.theme import render_mini_strip

RESULT_MAP = {"H": "Local", "D": "Empate", "A": "Visitante"}


def _last_results_html(matches, team: str, n: int = 10) -> str:
    team_m = (
        matches[(matches["home_team"] == team) | (matches["away_team"] == team)]
        .sort_values("match_date", ascending=False)
        .head(n)
    )

    if team_m.empty:
        return ""

    html = '<div class="track-panel"><div class="tp-head"><h2>Ultimos resultados</h2></div>'
    for _, m in team_m.iterrows():
        is_home = m["home_team"] == team
        if is_home:
            res = "W" if m["ft_result"] == "H" else ("D" if m["ft_result"] == "D" else "L")
        else:
            res = "W" if m["ft_result"] == "A" else ("D" if m["ft_result"] == "D" else "L")

        res_cls = {"W": "ok", "D": "", "L": "no"}[res]
        res_icon = {"W": "W", "D": "D", "L": "L"}[res]
        score = f"{int(m['ft_home_goals'])}–{int(m['ft_away_goals'])}"
        opp = m["away_team"] if is_home else m["home_team"]
        venue = "vs" if is_home else "@"
        d = str(m["match_date"])
        if len(d) > 5:
            d = d[5:]

        html += (
            f'<div class="tp-row">'
            f'<span class="tp-date">{d}</span>'
            f'<span class="tp-match">{venue} {opp}</span>'
            f'<span class="tp-score">{score}</span>'
            f'<span class="tp-pred">{res_icon}</span>'
            f'<span class="tp-icon"><span class="tp-check {res_cls}">'
            f"{'W' if res == 'W' else ('D' if res == 'D' else 'L')}</span></span>"
            f"</div>"
        )
    html += "</div>"
    return html


def render():
    render_mini_strip("Analisis de Equipo", "Analisis", "search")

    league_keys = list(DIVISION_NAMES.keys())

    with ui.row().classes("items-end gap-4 mt-4 mb-4"):
        league_sel = (
            ui.select(
                {k: DIVISION_NAMES[k] for k in league_keys}, value=league_keys[0], label="Liga"
            )
            .props('outlined dense dark color="orange-8"')
            .classes("w-48")
        )

        season_sel = (
            ui.select({}, value=None, label="Temporada")
            .props('outlined dense dark color="orange-8"')
            .classes("w-40")
        )

        team_sel = (
            ui.select({}, value=None, label="Equipo")
            .props('outlined dense dark color="orange-8"')
            .classes("w-52")
        )

    content = ui.element("div").classes("w-full")

    def update_seasons():
        seasons = get_seasons(league_sel.value)
        season_sel.options = {s: s for s in seasons} if seasons else {}
        season_sel.value = seasons[0] if seasons else None
        update_teams()

    def update_teams():
        if not season_sel.value:
            return
        teams = get_teams(league_sel.value, season=season_sel.value)
        team_sel.options = {t: t for t in teams} if teams else {}
        team_sel.value = teams[0] if teams else None
        load_data()

    def load_data():
        content.clear()
        if not team_sel.value or not season_sel.value:
            return

        team = team_sel.value
        matches = load_matches(division=league_sel.value, season=season_sel.value)
        if matches.empty:
            with content:
                ui.html(
                    '<div class="placeholder-box">'
                    '<div class="ph-title">No hay datos disponibles.</div></div>'
                )
            return

        home = matches[matches["home_team"] == team]
        away = matches[matches["away_team"] == team]
        total_p = len(home) + len(away)
        total_w = len(home[home["ft_result"] == "H"]) + len(away[away["ft_result"] == "A"])
        total_d = len(home[home["ft_result"] == "D"]) + len(away[away["ft_result"] == "D"])
        total_l = total_p - total_w - total_d
        gf = int(home["ft_home_goals"].sum() + away["ft_away_goals"].sum())
        ga = int(home["ft_away_goals"].sum() + away["ft_home_goals"].sum())
        diff = gf - ga
        sign = "+" if diff > 0 else ""
        ppg = total_w * 3 + total_d
        ppg_avg = f"{ppg / total_p:.2f}" if total_p else "—"
        win_pct = f"{total_w / total_p:.0%}" if total_p else "—"

        with content:
            ui.html(
                f'<div class="kpi-row">'
                f'<div class="kpi"><div class="kpi-val">{total_w}W {total_d}D {total_l}L</div>'
                f'<div class="kpi-lbl">{win_pct} victorias · {total_p} partidos</div></div>'
                f'<div class="kpi"><div class="kpi-val">{gf} / {ga}</div>'
                f'<div class="kpi-lbl">GF / GC · Dif: {sign}{diff}</div></div>'
                f'<div class="kpi"><div class="kpi-val">{ppg}</div>'
                f'<div class="kpi-lbl">{ppg_avg} pts/partido</div></div>'
                f"</div>"
            )

            # Home vs Away breakdown
            home_w = len(home[home["ft_result"] == "H"])
            home_d = len(home[home["ft_result"] == "D"])
            home_l = len(home) - home_w - home_d
            away_w = len(away[away["ft_result"] == "A"])
            away_d = len(away[away["ft_result"] == "D"])
            away_l = len(away) - away_w - away_d

            ui.html(
                '<div class="match-list">'
                '<div class="ml-head"><h2>Local vs Visitante</h2></div>'
                f'<div class="tp-row" style="font-weight:600">'
                f'<span class="tp-date">Sede</span>'
                f'<span class="tp-match">PJ</span>'
                f'<span class="tp-score">PG</span>'
                f'<span class="tp-pred">PE</span>'
                f'<span class="tp-icon">PP</span></div>'
                f'<div class="tp-row">'
                f'<span class="tp-date">Local</span>'
                f'<span class="tp-match">{len(home)}</span>'
                f'<span class="tp-score" style="color:var(--hit)">{home_w}</span>'
                f'<span class="tp-pred" style="color:var(--draw-color)">{home_d}</span>'
                f'<span class="tp-icon" style="color:var(--miss)">{home_l}</span></div>'
                f'<div class="tp-row">'
                f'<span class="tp-date">Visitante</span>'
                f'<span class="tp-match">{len(away)}</span>'
                f'<span class="tp-score" style="color:var(--hit)">{away_w}</span>'
                f'<span class="tp-pred" style="color:var(--draw-color)">{away_d}</span>'
                f'<span class="tp-icon" style="color:var(--miss)">{away_l}</span></div>'
                "</div>"
            )

            ui.html(_last_results_html(matches, team))

    league_sel.on("update:model-value", lambda: update_seasons())
    season_sel.on("update:model-value", lambda: update_teams())
    team_sel.on("update:model-value", lambda: load_data())

    update_seasons()

"""Match Comparator — head-to-head team comparison."""

from nicegui import ui

from webapp.data import DIVISION_NAMES, get_seasons, get_teams, load_features, load_matches
from webapp.theme import render_mini_strip


def render():
    render_mini_strip("Comparador de Equipos", "Analisis", "scale")

    league_keys = list(DIVISION_NAMES.keys())

    with ui.row().classes("items-end gap-4 mt-4 mb-4"):
        league_sel = (
            ui.select(
                {k: DIVISION_NAMES[k] for k in league_keys}, value=league_keys[0], label="Liga"
            )
            .props('outlined dense dark color="orange-8"')
            .classes("w-48")
        )

        team_a_sel = (
            ui.select({}, value=None, label="Equipo A")
            .props('outlined dense dark color="orange-8"')
            .classes("w-52")
        )

        team_b_sel = (
            ui.select({}, value=None, label="Equipo B")
            .props('outlined dense dark color="orange-8"')
            .classes("w-52")
        )

    content = ui.element("div").classes("w-full")

    def update_teams():
        seasons = get_seasons(league_sel.value)
        current = seasons[0] if seasons else None
        teams = get_teams(league_sel.value, season=current)
        opts = {t: t for t in teams} if teams else {}
        team_a_sel.options = opts
        team_b_sel.options = opts
        if teams and len(teams) >= 2:
            team_a_sel.value = teams[0]
            team_b_sel.value = teams[1]
        load_data()

    def load_data():
        content.clear()
        a = team_a_sel.value
        b = team_b_sel.value
        if not a or not b or a == b:
            return

        matches = load_matches(division=league_sel.value)
        if matches.empty:
            with content:
                ui.html(
                    '<div class="placeholder-box"><div class="ph-title">No hay datos.</div></div>'
                )
            return

        # H2H
        h2h = matches[
            ((matches["home_team"] == a) & (matches["away_team"] == b))
            | ((matches["home_team"] == b) & (matches["away_team"] == a))
        ].sort_values("match_date", ascending=False)

        a_wins = 0
        b_wins = 0
        draws = 0
        for _, m in h2h.iterrows():
            if m["home_team"] == a:
                if m["ft_result"] == "H":
                    a_wins += 1
                elif m["ft_result"] == "A":
                    b_wins += 1
                else:
                    draws += 1
            else:
                if m["ft_result"] == "A":
                    a_wins += 1
                elif m["ft_result"] == "H":
                    b_wins += 1
                else:
                    draws += 1

        with content:
            ui.html(
                f'<div class="kpi-row">'
                f'<div class="kpi"><div class="kpi-val" style="color:var(--hit)">{a_wins}</div>'
                f'<div class="kpi-lbl">{a}</div></div>'
                f'<div class="kpi"><div class="kpi-val" style="color:var(--draw-color)">{draws}</div>'
                f'<div class="kpi-lbl">Empates ({len(h2h)} partidos)</div></div>'
                f'<div class="kpi"><div class="kpi-val" style="color:var(--info)">{b_wins}</div>'
                f'<div class="kpi-lbl">{b}</div></div>'
                f"</div>"
            )

            # Comparison bars
            features = load_features()
            if not features.empty:
                import pandas as pd

                fa = features[features["team"] == a]
                fb = features[features["team"] == b]
                if not fa.empty and not fb.empty:
                    la = fa.sort_values("match_date").iloc[-1]
                    lb = fb.sort_values("match_date").iloc[-1]

                    compare_cols = [
                        ("goals_scored_avg", "Ataque (goles)"),
                        ("goals_conceded_avg", "Defensa (goles rec.)"),
                        ("win_rate", "% Victorias"),
                        ("xg_for_avg", "xG"),
                        ("shots_target_avg", "Tiros a puerta"),
                        ("corners_avg", "Corners"),
                    ]

                    bars_html = '<div class="compare-section">'
                    for col, label in compare_cols:
                        va = float(la.get(col, 0)) if pd.notna(la.get(col)) else 0
                        vb = float(lb.get(col, 0)) if pd.notna(lb.get(col)) else 0
                        mx = max(va, vb, 0.01)
                        pa = va / mx * 45
                        pb = vb / mx * 45

                        bars_html += (
                            f'<div class="cmp-row">'
                            f'<span class="cmp-val" style="color:var(--hit)">{va:.2f}</span>'
                            f'<div class="cmp-track">'
                            f'<div class="cmp-bar-a" style="width:{pa:.0f}%"></div>'
                            f'<div class="cmp-bar-b" style="width:{pb:.0f}%"></div>'
                            f"</div>"
                            f'<span class="cmp-val" style="color:var(--info)">{vb:.2f}</span>'
                            f"</div>"
                            f'<div class="cmp-label">{label}</div>'
                        )
                    bars_html += "</div>"
                    ui.html(bars_html)

            # H2H match history
            if not h2h.empty:
                h_html = (
                    '<div class="track-panel" style="margin-top:16px">'
                    '<div class="tp-head"><h2>Enfrentamientos directos</h2></div>'
                )
                for _, m in h2h.head(10).iterrows():
                    score = f"{int(m['ft_home_goals'])}–{int(m['ft_away_goals'])}"
                    d = str(m["match_date"])
                    if len(d) > 5:
                        d = d[5:]
                    h_html += (
                        f'<div class="tp-row">'
                        f'<span class="tp-date">{d}</span>'
                        f'<span class="tp-match">{m["home_team"]} vs {m["away_team"]}</span>'
                        f'<span class="tp-score">{score}</span>'
                        f'<span class="tp-pred"></span>'
                        f'<span class="tp-icon"></span>'
                        f"</div>"
                    )
                h_html += "</div>"
                ui.html(h_html)
            else:
                ui.html(
                    '<div class="placeholder-box" style="margin-top:16px">'
                    '<div class="ph-title">No se encontraron enfrentamientos directos.</div></div>'
                )

    league_sel.on("update:model-value", lambda: update_teams())
    team_a_sel.on("update:model-value", lambda: load_data())
    team_b_sel.on("update:model-value", lambda: load_data())

    update_teams()

"""Liga Overview — standings, form, and stats for each league."""

from nicegui import ui

from webapp.data import DIVISION_NAMES, get_seasons, load_matches
from webapp.theme import render_mini_strip


def _form_dots(matches, team: str, last_n: int = 5) -> str:
    team_matches = (
        matches[(matches["home_team"] == team) | (matches["away_team"] == team)]
        .sort_values("match_date", ascending=False)
        .head(last_n)
    )

    dots = ""
    for _, m in team_matches.iterrows():
        if m["home_team"] == team:
            if m["ft_result"] == "H":
                cls = "w"
            elif m["ft_result"] == "D":
                cls = "d"
            else:
                cls = "l"
        else:
            if m["ft_result"] == "A":
                cls = "w"
            elif m["ft_result"] == "D":
                cls = "d"
            else:
                cls = "l"
        label = {"w": "W", "d": "D", "l": "L"}[cls]
        dots += f'<div class="dot {cls}">{label}</div>'
    return f'<div class="streak">{dots}</div>'


def _standings_table(matches) -> list[dict]:
    teams = set(matches["home_team"].unique()) | set(matches["away_team"].unique())
    stats = {t: {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0} for t in teams}

    for _, m in matches.iterrows():
        h, a = m["home_team"], m["away_team"]
        hg, ag = m["ft_home_goals"], m["ft_away_goals"]
        if hg is None or ag is None:
            continue
        stats[h]["PJ"] += 1
        stats[a]["PJ"] += 1
        stats[h]["GF"] += hg
        stats[h]["GC"] += ag
        stats[a]["GF"] += ag
        stats[a]["GC"] += hg
        if hg > ag:
            stats[h]["PG"] += 1
            stats[a]["PP"] += 1
        elif hg < ag:
            stats[a]["PG"] += 1
            stats[h]["PP"] += 1
        else:
            stats[h]["PE"] += 1
            stats[a]["PE"] += 1

    rows = []
    for t in teams:
        s = stats[t]
        pts = s["PG"] * 3 + s["PE"]
        rows.append({"team": t, "Pts": pts, "DIF": s["GF"] - s["GC"], **s})
    rows.sort(key=lambda r: (-r["Pts"], -r["DIF"], -r["GF"]))
    return rows


def render():
    render_mini_strip("Liga Overview", "Analisis", "grid")

    league_keys = list(DIVISION_NAMES.keys())
    league_opts = {k: DIVISION_NAMES[k] for k in league_keys}

    with ui.row().classes("items-end gap-4 mt-4 mb-4"):
        league_sel = (
            ui.select(league_opts, value=league_keys[0], label="Liga")
            .props('outlined dense dark color="orange-8"')
            .classes("w-52")
        )

        season_sel = (
            ui.select({}, value=None, label="Temporada")
            .props('outlined dense dark color="orange-8"')
            .classes("w-40")
        )

    content = ui.element("div").classes("w-full")

    def update_seasons():
        seasons = get_seasons(league_sel.value)
        season_sel.options = {s: s for s in seasons} if seasons else {"Sin datos": "Sin datos"}
        season_sel.value = seasons[0] if seasons else "Sin datos"
        load_table()

    def load_table():
        content.clear()
        league = league_sel.value
        season = season_sel.value
        if not league or season == "Sin datos":
            return

        matches = load_matches(division=league, season=season)
        if matches.empty:
            with content:
                ui.html(
                    '<div class="placeholder-box">'
                    '<div class="ph-title">No hay datos para esta temporada.</div>'
                    "</div>"
                )
            return

        standings = _standings_table(matches)

        with content:
            total_m = len(matches)
            total_t = len(standings)
            ui.html(
                f'<div class="kpi-row">'
                f'<div class="kpi"><div class="kpi-val">{total_t}</div><div class="kpi-lbl">Equipos</div></div>'
                f'<div class="kpi"><div class="kpi-val">{total_m}</div><div class="kpi-lbl">Partidos</div></div>'
                f'<div class="kpi"><div class="kpi-val">{season}</div><div class="kpi-lbl">Temporada</div></div>'
                f"</div>"
            )

            table_html = (
                '<div class="standings-panel">'
                '<div class="ml-head"><h2>Tabla de Posiciones</h2></div>'
                '<div class="st-table">'
                '<div class="st-header">'
                '<span class="st-pos">#</span>'
                '<span class="st-team">Equipo</span>'
                '<span class="st-num">Pts</span>'
                '<span class="st-num">PJ</span>'
                '<span class="st-num">PG</span>'
                '<span class="st-num">PE</span>'
                '<span class="st-num">PP</span>'
                '<span class="st-num">GF</span>'
                '<span class="st-num">GC</span>'
                '<span class="st-num">DIF</span>'
                '<span class="st-form">Racha</span>'
                "</div>"
            )

            for i, row in enumerate(standings):
                cls = ""
                if i < 4:
                    cls = "ucl"
                elif i >= len(standings) - 3:
                    cls = "rel"
                dif = f"+{row['DIF']}" if row["DIF"] > 0 else str(row["DIF"])
                form = _form_dots(matches, row["team"])
                table_html += (
                    f'<div class="st-row {cls}">'
                    f'<span class="st-pos">{i + 1}</span>'
                    f'<span class="st-team">{row["team"]}</span>'
                    f'<span class="st-num st-pts">{row["Pts"]}</span>'
                    f'<span class="st-num">{row["PJ"]}</span>'
                    f'<span class="st-num">{row["PG"]}</span>'
                    f'<span class="st-num">{row["PE"]}</span>'
                    f'<span class="st-num">{row["PP"]}</span>'
                    f'<span class="st-num">{row["GF"]}</span>'
                    f'<span class="st-num">{row["GC"]}</span>'
                    f'<span class="st-num">{dif}</span>'
                    f'<span class="st-form">{form}</span>'
                    f"</div>"
                )

            table_html += "</div></div>"
            ui.html(table_html)

    league_sel.on("update:model-value", lambda: update_seasons())
    season_sel.on("update:model-value", lambda: load_table())

    update_seasons()

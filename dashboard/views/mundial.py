"""FIFA World Cup 2026 — Fase de Grupos, Simulador y Bracket."""

import streamlit as st
import streamlit.components.v1 as components

from dashboard.components.theme import page_header
from dashboard.data_access import get_supabase_client

WC_GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Korea", "Czechia", "South Africa"],
    "B": ["Canada", "Bosnia Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Argentina", "Algeria", "Austria", "Jordan"],
    "G": ["France", "Norway", "Senegal", "Iraq"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde Islands"],
    "I": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "J": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "K": ["Portugal", "Colombia", "Congo DR", "Uzbekistan"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

FLAGS = {
    "Algeria": "🇩🇿",
    "Argentina": "🇦🇷",
    "Australia": "🇦🇺",
    "Austria": "🇦🇹",
    "Belgium": "🇧🇪",
    "Bosnia Herzegovina": "🇧🇦",
    "Brazil": "🇧🇷",
    "Canada": "🇨🇦",
    "Cape Verde Islands": "🇨🇻",
    "Colombia": "🇨🇴",
    "Congo DR": "🇨🇩",
    "Croatia": "🇭🇷",
    "Curacao": "🇨🇼",
    "Czechia": "🇨🇿",
    "Ecuador": "🇪🇨",
    "Egypt": "🇪🇬",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "France": "🇫🇷",
    "Germany": "🇩🇪",
    "Ghana": "🇬🇭",
    "Haiti": "🇭🇹",
    "Iran": "🇮🇷",
    "Iraq": "🇮🇶",
    "Ivory Coast": "🇨🇮",
    "Japan": "🇯🇵",
    "Jordan": "🇯🇴",
    "Mexico": "🇲🇽",
    "Morocco": "🇲🇦",
    "Netherlands": "🇳🇱",
    "New Zealand": "🇳🇿",
    "Norway": "🇳🇴",
    "Panama": "🇵🇦",
    "Paraguay": "🇵🇾",
    "Portugal": "🇵🇹",
    "Qatar": "🇶🇦",
    "Saudi Arabia": "🇸🇦",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Senegal": "🇸🇳",
    "South Africa": "🇿🇦",
    "South Korea": "🇰🇷",
    "Spain": "🇪🇸",
    "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭",
    "Tunisia": "🇹🇳",
    "Turkey": "🇹🇷",
    "United States": "🇺🇸",
    "Uruguay": "🇺🇾",
    "Uzbekistan": "🇺🇿",
}

CODES = {
    "Algeria": "ALG",
    "Argentina": "ARG",
    "Australia": "AUS",
    "Austria": "AUT",
    "Belgium": "BEL",
    "Bosnia Herzegovina": "BIH",
    "Brazil": "BRA",
    "Canada": "CAN",
    "Cape Verde Islands": "CPV",
    "Colombia": "COL",
    "Congo DR": "COD",
    "Croatia": "CRO",
    "Curacao": "CUW",
    "Czechia": "CZE",
    "Ecuador": "ECU",
    "Egypt": "EGY",
    "England": "ENG",
    "France": "FRA",
    "Germany": "GER",
    "Ghana": "GHA",
    "Haiti": "HAI",
    "Iran": "IRN",
    "Iraq": "IRQ",
    "Ivory Coast": "CIV",
    "Japan": "JPN",
    "Jordan": "JOR",
    "Mexico": "MEX",
    "Morocco": "MAR",
    "Netherlands": "NED",
    "New Zealand": "NZL",
    "Norway": "NOR",
    "Panama": "PAN",
    "Paraguay": "PAR",
    "Portugal": "POR",
    "Qatar": "QAT",
    "Saudi Arabia": "KSA",
    "Scotland": "SCO",
    "Senegal": "SEN",
    "South Africa": "RSA",
    "South Korea": "KOR",
    "Spain": "ESP",
    "Sweden": "SWE",
    "Switzerland": "SUI",
    "Tunisia": "TUN",
    "Turkey": "TUR",
    "United States": "USA",
    "Uruguay": "URU",
    "Uzbekistan": "UZB",
}

_GROUP_TEAMS = set()
for _teams in WC_GROUPS.values():
    _GROUP_TEAMS.update(_teams)
_TEAM_TO_GROUP = {}
for _letter, _teams in WC_GROUPS.items():
    for _t in _teams:
        _TEAM_TO_GROUP[_t] = _letter


def _flag(team: str) -> str:
    return FLAGS.get(team, "")


def _code(team: str) -> str:
    return CODES.get(team, team[:3].upper())


# ── Data ─────────────────────────────────────────────────


@st.cache_data(ttl=120)
def _load_wc_matches() -> list[dict]:
    client = get_supabase_client()
    resp = (
        client.table("matches")
        .select("home_team,away_team,match_date,ft_result,ft_home_goals,ft_away_goals")
        .eq("division", "WC")
        .order("match_date")
        .execute()
    )
    return resp.data or []


def _group_matches(all_matches: list[dict], teams: list[str]) -> list[dict]:
    s = set(teams)
    return [m for m in all_matches if m["home_team"] in s and m["away_team"] in s]


def _knockout_matches(all_matches: list[dict]) -> list[dict]:
    return [
        m
        for m in all_matches
        if _TEAM_TO_GROUP.get(m["home_team"]) != _TEAM_TO_GROUP.get(m["away_team"])
    ]


# ── Standings ────────────────────────────────────────────


def _calc_standings(teams: list[str], matches: list[dict], simulated: dict) -> list[dict]:
    stats = {t: {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0} for t in teams}

    for m in matches:
        home, away = m["home_team"], m["away_team"]
        if m["ft_result"] is not None:
            hg, ag = m["ft_home_goals"], m["ft_away_goals"]
        elif (home, away) in simulated:
            hg, ag = simulated[(home, away)]
        else:
            continue

        if hg is None or ag is None:
            continue

        stats[home]["PJ"] += 1
        stats[away]["PJ"] += 1
        stats[home]["GF"] += hg
        stats[home]["GC"] += ag
        stats[away]["GF"] += ag
        stats[away]["GC"] += hg

        if hg > ag:
            stats[home]["PG"] += 1
            stats[away]["PP"] += 1
        elif hg < ag:
            stats[away]["PG"] += 1
            stats[home]["PP"] += 1
        else:
            stats[home]["PE"] += 1
            stats[away]["PE"] += 1

    rows = []
    for t in teams:
        s = stats[t]
        pts = s["PG"] * 3 + s["PE"]
        rows.append({"team": t, "Pts": pts, "DIF": s["GF"] - s["GC"], **s})

    rows.sort(key=lambda r: (-r["Pts"], -r["DIF"], -r["GF"]))
    return rows


def _collect_simulated(all_matches: list[dict]) -> dict:
    sim = {}
    for letter, teams in WC_GROUPS.items():
        for m in _group_matches(all_matches, teams):
            if m["ft_result"] is not None:
                continue
            home, away = m["home_team"], m["away_team"]
            hg = st.session_state.get(f"wc_{letter}_{home}_{away}_h")
            ag = st.session_state.get(f"wc_{letter}_{home}_{away}_a")
            if hg is not None and ag is not None:
                sim[(home, away)] = (int(hg), int(ag))
    return sim


# ── Overview Section ─────────────────────────────────────


def _group_card_html(letter: str, standings: list[dict]) -> str:
    html = (
        '<div style="border:1px solid #333;border-radius:8px;padding:10px;'
        'background:#0e1117;height:100%;">'
        f'<div style="font-weight:bold;color:#ffa726;margin-bottom:6px;'
        f'font-size:0.95rem;">Grupo {letter}</div>'
    )
    for i, row in enumerate(standings):
        bg = ""
        if i < 2:
            bg = "background:rgba(76,175,80,0.12);"
        elif i == 2:
            bg = "background:rgba(255,193,7,0.08);"
        t = row["team"]
        dif = f"+{row['DIF']}" if row["DIF"] > 0 else str(row["DIF"])
        html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:4px 6px;font-size:0.82rem;border-radius:3px;{bg}">'
            f"<span>{_flag(t)} {_code(t)}</span>"
            f"<span><b>{row['Pts']}</b> "
            f'<small style="color:#888">({dif})</small></span>'
            "</div>"
        )
    html += "</div>"
    return html


def _render_overview(all_matches: list[dict], simulated: dict):
    st.markdown("### Fase de Grupos")
    st.caption(
        "🟢 Clasifica directo (1° y 2°) · 🟡 Posible clasificacion (mejor 3°) · ⬜ Eliminado"
    )

    letters = list(WC_GROUPS.keys())
    for row_start in range(0, 12, 4):
        cols = st.columns(4, gap="small")
        for i, col in enumerate(cols):
            idx = row_start + i
            letter = letters[idx]
            teams = WC_GROUPS[letter]
            gm = _group_matches(all_matches, teams)
            standings = _calc_standings(teams, gm, simulated)
            with col:
                st.markdown(_group_card_html(letter, standings), unsafe_allow_html=True)


# ── Simulator Section ────────────────────────────────────


def _standings_html(standings: list[dict]) -> str:
    html = (
        '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;'
        'margin-bottom:12px;">'
        "<thead><tr style='border-bottom:2px solid #555;color:#888;'>"
        '<th style="text-align:left;padding:4px 6px;">#</th>'
        '<th style="text-align:left;padding:4px 6px;">Equipo</th>'
        '<th style="text-align:center;padding:4px 3px;">Pts</th>'
        '<th style="text-align:center;padding:4px 3px;">PJ</th>'
        '<th style="text-align:center;padding:4px 3px;">PG</th>'
        '<th style="text-align:center;padding:4px 3px;">PE</th>'
        '<th style="text-align:center;padding:4px 3px;">PP</th>'
        '<th style="text-align:center;padding:4px 3px;">GF</th>'
        '<th style="text-align:center;padding:4px 3px;">GC</th>'
        '<th style="text-align:center;padding:4px 3px;">DIF</th>'
        "</tr></thead><tbody>"
    )
    for i, row in enumerate(standings):
        bg = ""
        if i < 2:
            bg = "background:rgba(76,175,80,0.12);"
        elif i == 2:
            bg = "background:rgba(255,193,7,0.08);"
        t = row["team"]
        dif = f"+{row['DIF']}" if row["DIF"] > 0 else str(row["DIF"])
        html += (
            f'<tr style="border-bottom:1px solid #333;{bg}">'
            f'<td style="padding:5px 6px;">{i + 1}</td>'
            f'<td style="padding:5px 6px;">{_flag(t)} {_code(t)}</td>'
            f'<td style="text-align:center;font-weight:bold;">{row["Pts"]}</td>'
            f'<td style="text-align:center;">{row["PJ"]}</td>'
            f'<td style="text-align:center;">{row["PG"]}</td>'
            f'<td style="text-align:center;">{row["PE"]}</td>'
            f'<td style="text-align:center;">{row["PP"]}</td>'
            f'<td style="text-align:center;">{row["GF"]}</td>'
            f'<td style="text-align:center;">{row["GC"]}</td>'
            f'<td style="text-align:center;">{dif}</td>'
            "</tr>"
        )
    html += "</tbody></table>"
    return html


def _render_simulator(all_matches: list[dict]):
    st.markdown("### Simular Resultados")
    st.caption("Ingresa marcadores para ver como cambian las tablas de posiciones.")

    if st.button("🔄 Reset simulacion"):
        for key in list(st.session_state.keys()):
            if key.startswith("wc_"):
                del st.session_state[key]
        st.rerun()

    tabs = st.tabs([f"Grupo {gl}" for gl in WC_GROUPS])

    for tab, (letter, teams) in zip(tabs, WC_GROUPS.items()):
        with tab:
            gm = _group_matches(all_matches, teams)

            sim: dict[tuple, tuple] = {}
            for m in gm:
                if m["ft_result"] is not None:
                    continue
                h, a = m["home_team"], m["away_team"]
                hg = st.session_state.get(f"wc_{letter}_{h}_{a}_h")
                ag = st.session_state.get(f"wc_{letter}_{h}_{a}_a")
                if hg is not None and ag is not None:
                    sim[(h, a)] = (int(hg), int(ag))

            standings = _calc_standings(teams, gm, sim)
            st.markdown(_standings_html(standings), unsafe_allow_html=True)

            st.markdown("**Partidos**")
            for m in gm:
                home, away = m["home_team"], m["away_team"]
                played = m["ft_result"] is not None

                c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1, 0.4, 1, 2.5, 2])

                with c1:
                    st.markdown(
                        f"<div style='text-align:right;padding-top:6px;'>"
                        f"{_flag(home)} <b>{_code(home)}</b></div>",
                        unsafe_allow_html=True,
                    )

                if played:
                    with c2:
                        st.markdown(
                            f"<div style='text-align:center;padding-top:6px;'>"
                            f"<b>{m['ft_home_goals']}</b></div>",
                            unsafe_allow_html=True,
                        )
                    with c3:
                        st.markdown(
                            "<div style='text-align:center;padding-top:6px;'>-</div>",
                            unsafe_allow_html=True,
                        )
                    with c4:
                        st.markdown(
                            f"<div style='text-align:center;padding-top:6px;'>"
                            f"<b>{m['ft_away_goals']}</b></div>",
                            unsafe_allow_html=True,
                        )
                else:
                    with c2:
                        st.number_input(
                            "h",
                            min_value=0,
                            max_value=20,
                            value=None,
                            key=f"wc_{letter}_{home}_{away}_h",
                            label_visibility="collapsed",
                        )
                    with c3:
                        st.markdown(
                            "<div style='text-align:center;padding-top:6px;'>-</div>",
                            unsafe_allow_html=True,
                        )
                    with c4:
                        st.number_input(
                            "a",
                            min_value=0,
                            max_value=20,
                            value=None,
                            key=f"wc_{letter}_{home}_{away}_a",
                            label_visibility="collapsed",
                        )

                with c5:
                    st.markdown(
                        f"<div style='padding-top:6px;'><b>{_code(away)}</b> {_flag(away)}</div>",
                        unsafe_allow_html=True,
                    )
                with c6:
                    st.caption(f"📅 {m['match_date']}")


# ── Bracket Section ──────────────────────────────────────

R32_LEFT = [
    [("1A", "3°"), ("2C", "2D")],
    [("1B", "3°"), ("1C", "3°")],
    [("1E", "3°"), ("2A", "2B")],
    [("1D", "3°"), ("2E", "2F")],
]

R32_RIGHT = [
    [("1G", "3°"), ("2I", "2J")],
    [("1F", "3°"), ("1H", "3°")],
    [("1J", "3°"), ("2G", "2H")],
    [("1I", "3°"), ("2K", "2L")],
]


def _build_bracket_html(ko_matches: list[dict]) -> str:
    ko_map: dict[tuple, dict] = {}
    for m in ko_matches:
        ko_map[(m["home_team"], m["away_team"])] = m

    def _game(t1: str, t2: str, s1: str = "", s2: str = "", hl: bool = False) -> str:
        border = "border-color:#ffa726;" if hl else ""
        return (
            f'<div class="game" style="{border}">'
            f'<div class="tr"><span>{t1}</span><span class="sc">{s1}</span></div>'
            f'<div class="tr"><span>{t2}</span><span class="sc">{s2}</span></div>'
            "</div>"
        )

    def _pair_html(pair: list[tuple]) -> str:
        items = ""
        for t1, t2 in pair:
            items += _game(t1, t2)
        return f'<div class="pair">{items}</div>'

    def _slot(t1: str = "---", t2: str = "---", **kw) -> str:
        return f'<div class="slot">{_game(t1, t2, **kw)}</div>'

    def _conn_col(n: int, cls: str) -> str:
        return '<div class="conns">' + f'<div class="{cls}"></div>' * n + "</div>"

    r32l = "".join(_pair_html(p) for p in R32_LEFT)
    r32r = "".join(_pair_html(p) for p in R32_RIGHT)
    slots4 = _slot() * 4
    slots2 = _slot() * 2
    slot1 = _slot()

    final_box = (
        '<div class="final-col">'
        '<div class="fl">🏆 Final</div>'
        + _game("---", "---", hl=True)
        + '<div style="height:24px;"></div>'
        '<div class="fl" style="color:#888;">3er Puesto</div>' + _game("---", "---") + "</div>"
    )

    return f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;color:#fafafa;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
.wrap{{overflow-x:auto;padding:8px 0}}
.labels{{display:flex;align-items:center}}
.labels span{{min-width:110px;text-align:center;font-size:10px;color:#888;
  text-transform:uppercase;letter-spacing:1px}}
.labels .cs{{width:16px}}
.bracket{{display:flex;align-items:stretch;min-height:520px;margin-top:6px}}
.round{{display:flex;flex-direction:column;min-width:110px;margin:0 2px}}
.pair{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:4px}}
.slot{{flex:1;display:flex;align-items:center}}
.game{{border:1px solid #444;border-radius:4px;background:#1a1a2e;width:100%}}
.tr{{display:flex;justify-content:space-between;padding:3px 6px;font-size:11px}}
.tr+.tr{{border-top:1px solid #333}}
.sc{{font-weight:bold;color:#ffa726}}
.conns{{display:flex;flex-direction:column;width:16px}}
.cl{{flex:1;position:relative}}
.cl::before{{content:'';position:absolute;left:0;width:8px;top:25%;height:50%;
  border:1.5px solid #555;border-left:none;border-radius:0 3px 3px 0}}
.cl::after{{content:'';position:absolute;left:8px;right:0;top:50%;
  border-top:1.5px solid #555}}
.cr{{flex:1;position:relative}}
.cr::before{{content:'';position:absolute;right:0;width:8px;top:25%;height:50%;
  border:1.5px solid #555;border-right:none;border-radius:3px 0 0 3px}}
.cr::after{{content:'';position:absolute;right:8px;left:0;top:50%;
  border-top:1.5px solid #555}}
.hl{{flex:1;position:relative}}
.hl::after{{content:'';position:absolute;left:0;right:0;top:50%;
  border-top:1.5px solid #555}}
.final-col{{display:flex;flex-direction:column;min-width:120px;
  justify-content:center;align-items:center}}
.fl{{font-size:12px;font-weight:bold;color:#ffa726;text-align:center;margin-bottom:4px}}
.final-col .game{{width:110px}}
</style></head><body>
<div class="wrap">
<div class="labels">
  <span>16avos</span><div class="cs"></div>
  <span>8avos</span><div class="cs"></div>
  <span>4tos</span><div class="cs"></div>
  <span>Semis</span><div class="cs"></div>
  <span style="min-width:120px">FINAL</span><div class="cs"></div>
  <span>Semis</span><div class="cs"></div>
  <span>4tos</span><div class="cs"></div>
  <span>8avos</span><div class="cs"></div>
  <span>16avos</span>
</div>
<div class="bracket">
  <div class="round">{r32l}</div>
  {_conn_col(4, "cl")}
  <div class="round">{slots4}</div>
  {_conn_col(2, "cl")}
  <div class="round">{slots2}</div>
  {_conn_col(1, "cl")}
  <div class="round">{slot1}</div>
  <div class="conns"><div class="hl"></div></div>
  {final_box}
  <div class="conns"><div class="hl"></div></div>
  <div class="round">{slot1}</div>
  {_conn_col(1, "cr")}
  <div class="round">{slots2}</div>
  {_conn_col(2, "cr")}
  <div class="round">{slots4}</div>
  {_conn_col(4, "cr")}
  <div class="round">{r32r}</div>
</div>
</div>
</body></html>"""


def _render_bracket(all_matches: list[dict]):
    st.markdown("### Fase Eliminatoria")
    st.caption("El bracket se actualiza automaticamente con los resultados de los partidos.")

    ko = _knockout_matches(all_matches)
    html = _build_bracket_html(ko)
    components.html(html, height=620, scrolling=True)

    if ko:
        st.markdown("**Partidos de eliminatoria**")
        for m in ko:
            home, away = m["home_team"], m["away_team"]
            if m["ft_result"] is not None:
                score = f"{m['ft_home_goals']} - {m['ft_away_goals']}"
            else:
                score = "vs"
            st.markdown(
                f"{_flag(home)} **{_code(home)}** {score} **{_code(away)}** {_flag(away)}"
                f"&nbsp;&nbsp;📅 {m['match_date']}"
            )


# ── Page ─────────────────────────────────────────────────

st.markdown(page_header("🏆", "FIFA World Cup 2026"), unsafe_allow_html=True)
st.caption("Estados Unidos · Mexico · Canada  |  11 junio — 19 julio 2026")

all_matches = _load_wc_matches()
simulated = _collect_simulated(all_matches)

played = sum(1 for m in all_matches if m["ft_result"] is not None)
total = len(all_matches)

m1, m2, m3 = st.columns(3)
m1.metric("Equipos", 48)
m2.metric("Partidos", total)
m3.metric("Jugados", played)

_render_overview(all_matches, simulated)
st.divider()
_render_simulator(all_matches)
st.divider()
_render_bracket(all_matches)

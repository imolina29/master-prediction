"""FIFA World Cup 2026 — Fase de Grupos, Simulador y Bracket."""

import streamlit as st
import streamlit.components.v1 as components

from dashboard.components.theme import eyebrow, page_title
from dashboard.data_access import get_supabase_client

WC_GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Korea", "Czechia", "South Africa"],
    "B": ["Canada", "Bosnia Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["France", "Norway", "Senegal", "Iraq"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde Islands"],
    "I": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
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


def _team_label(team: str) -> str:
    """Format team as flag + code for bracket display."""
    if not team:
        return "---"
    return f"{_flag(team)} {_code(team)}"


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
        '<div style="border:1px solid rgba(255,255,255,0.06);border-radius:16px;padding:12px;'
        'background:#0c1015;height:100%;">'
        f'<div style="font-weight:bold;color:#f5b020;margin-bottom:6px;'
        f'font-size:0.95rem;">Grupo {letter}</div>'
    )
    for i, row in enumerate(standings):
        bg = ""
        if i < 2:
            bg = "background:rgba(22,196,127,0.12);"
        elif i == 2:
            bg = "background:rgba(245,176,32,0.10);"
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
            bg = "background:rgba(22,196,127,0.12);"
        elif i == 2:
            bg = "background:rgba(245,176,32,0.10);"
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


def _resolve_bracket_data(all_matches: list[dict], simulated: dict) -> dict:
    """Resolve all bracket positions to actual teams and scores."""

    # -- group standings & position map --
    pos_map: dict[str, str] = {}
    for letter, teams in WC_GROUPS.items():
        gm = _group_matches(all_matches, teams)
        standings = _calc_standings(teams, gm, simulated)
        for i, row in enumerate(standings):
            pos_map[f"{i + 1}{letter}"] = row["team"]

    # -- knockout match pools by round --
    ko = _knockout_matches(all_matches)

    def _by_date(lo, hi):
        return [m for m in ko if lo <= m["match_date"] <= hi]

    r32_pool = [m for m in ko if m["match_date"] <= "2026-07-03"]
    r16_pool = _by_date("2026-07-04", "2026-07-08")
    qf_pool = _by_date("2026-07-09", "2026-07-12")
    sf_pool = _by_date("2026-07-13", "2026-07-16")
    final_pool = [m for m in ko if m["match_date"] >= "2026-07-17"]

    # -- helpers --
    def _find(pool, t1, t2):
        """Find match involving t1 vs t2 (either order)."""
        if not t1 or not t2:
            return None
        pair = {t1, t2}
        for m in pool:
            if {m["home_team"], m["away_team"]} == pair:
                return m
        return None

    def _find_for(pool, team):
        """Find first match involving *team*."""
        if not team:
            return None
        for m in pool:
            if team in (m["home_team"], m["away_team"]):
                return m
        return None

    def _winner(match, next_pool):
        """Return winner of a played match; for draws check next round."""
        if not match or match["ft_home_goals"] is None:
            return None
        h, a = match["home_team"], match["away_team"]
        hg, ag = match["ft_home_goals"], match["ft_away_goals"]
        if hg > ag:
            return h
        if ag > hg:
            return a
        for nm in next_pool:
            if h in (nm["home_team"], nm["away_team"]):
                return h
            if a in (nm["home_team"], nm["away_team"]):
                return a
        return None

    def _loser(match, next_pool):
        w = _winner(match, next_pool)
        if not w or not match:
            return None
        h, a = match["home_team"], match["away_team"]
        return a if w == h else h

    # -- resolve R32 --
    def _resolve_r32(template, pool):
        result = []
        for pair in template:
            pair_data = []
            for t1_tag, t2_tag in pair:
                t1 = pos_map.get(t1_tag)
                if t2_tag == "3°":
                    m = _find_for(pool, t1) if t1 else None
                    if m and t1:
                        t2 = m["away_team"] if m["home_team"] == t1 else m["home_team"]
                    else:
                        t2 = None
                else:
                    t2 = pos_map.get(t2_tag)
                match = _find(pool, t1, t2)
                pair_data.append({"t1": t1, "t2": t2, "match": match})
            result.append(pair_data)
        return result

    r32_left = _resolve_r32(R32_LEFT, r32_pool)
    r32_right = _resolve_r32(R32_RIGHT, r32_pool)

    # -- R16: winner of pair[i][0] vs winner of pair[i][1] --
    r16_left = []
    for pair in r32_left:
        w1 = _winner(pair[0]["match"], r16_pool)
        w2 = _winner(pair[1]["match"], r16_pool)
        m = _find(r16_pool, w1, w2)
        r16_left.append({"t1": w1, "t2": w2, "match": m})

    r16_right = []
    for pair in r32_right:
        w1 = _winner(pair[0]["match"], r16_pool)
        w2 = _winner(pair[1]["match"], r16_pool)
        m = _find(r16_pool, w1, w2)
        r16_right.append({"t1": w1, "t2": w2, "match": m})

    # -- QF: winner of R16[2j] vs winner of R16[2j+1] --
    qf_left = []
    for i in range(0, 4, 2):
        w1 = _winner(r16_left[i]["match"], qf_pool)
        w2 = _winner(r16_left[i + 1]["match"], qf_pool)
        m = _find(qf_pool, w1, w2)
        qf_left.append({"t1": w1, "t2": w2, "match": m})

    qf_right = []
    for i in range(0, 4, 2):
        w1 = _winner(r16_right[i]["match"], qf_pool)
        w2 = _winner(r16_right[i + 1]["match"], qf_pool)
        m = _find(qf_pool, w1, w2)
        qf_right.append({"t1": w1, "t2": w2, "match": m})

    # -- SF --
    sf_lw1 = _winner(qf_left[0]["match"], sf_pool)
    sf_lw2 = _winner(qf_left[1]["match"], sf_pool)
    sf_left_m = _find(sf_pool, sf_lw1, sf_lw2)
    sf_left = {"t1": sf_lw1, "t2": sf_lw2, "match": sf_left_m}

    sf_rw1 = _winner(qf_right[0]["match"], sf_pool)
    sf_rw2 = _winner(qf_right[1]["match"], sf_pool)
    sf_right_m = _find(sf_pool, sf_rw1, sf_rw2)
    sf_right = {"t1": sf_rw1, "t2": sf_rw2, "match": sf_right_m}

    # For SF penalty resolution, use only the actual final (latest date)
    # to avoid confusing it with the 3rd-place match.
    actual_final = max(final_pool, key=lambda m: m["match_date"]) if final_pool else None
    final_only = [actual_final] if actual_final else []

    # -- Final & 3rd place --
    final_t1 = _winner(sf_left_m, final_only)
    final_t2 = _winner(sf_right_m, final_only)
    final_m = _find(final_pool, final_t1, final_t2)
    final = {"t1": final_t1, "t2": final_t2, "match": final_m}

    third_t1 = _loser(sf_left_m, final_only)
    third_t2 = _loser(sf_right_m, final_only)
    third_m = _find(final_pool, third_t1, third_t2)
    third = {"t1": third_t1, "t2": third_t2, "match": third_m}

    return {
        "r32_left": r32_left,
        "r32_right": r32_right,
        "r16_left": r16_left,
        "r16_right": r16_right,
        "qf_left": qf_left,
        "qf_right": qf_right,
        "sf_left": sf_left,
        "sf_right": sf_right,
        "final": final,
        "third": third,
    }


def _build_bracket_html(data: dict) -> str:
    """Render the knockout bracket HTML from resolved *data*."""

    def _game(t1: str, t2: str, s1: str = "", s2: str = "", hl: bool = False) -> str:
        border = "border-color:#f5b020;" if hl else ""
        return (
            f'<div class="game" style="{border}">'
            f'<div class="tr"><span>{t1}</span>'
            f'<span class="sc">{s1}</span></div>'
            f'<div class="tr"><span>{t2}</span>'
            f'<span class="sc">{s2}</span></div>'
            "</div>"
        )

    def _md_game(md, hl: bool = False) -> str:
        """Render a match-data dict {t1, t2, match} as a game div."""
        t1 = _team_label(md["t1"]) if md else "---"
        t2 = _team_label(md["t2"]) if md else "---"
        s1, s2 = "", ""
        if md and md.get("match") and md["match"]["ft_home_goals"] is not None:
            m = md["match"]
            if m["home_team"] == md["t1"]:
                s1 = str(m["ft_home_goals"])
                s2 = str(m["ft_away_goals"])
            else:
                s1 = str(m["ft_away_goals"])
                s2 = str(m["ft_home_goals"])
        return _game(t1, t2, s1, s2, hl)

    def _pair_html(pair: list) -> str:
        items = "".join(_md_game(md) for md in pair)
        return f'<div class="pair">{items}</div>'

    def _slot(md) -> str:
        return f'<div class="slot">{_md_game(md)}</div>'

    def _conn_col(n: int, cls: str) -> str:
        return '<div class="conns">' + f'<div class="{cls}"></div>' * n + "</div>"

    # -- build columns --
    r32l = "".join(_pair_html(p) for p in data["r32_left"])
    r32r = "".join(_pair_html(p) for p in data["r32_right"])

    r16l = "".join(_slot(md) for md in data["r16_left"])
    r16r = "".join(_slot(md) for md in data["r16_right"])

    qfl = "".join(_slot(md) for md in data["qf_left"])
    qfr = "".join(_slot(md) for md in data["qf_right"])

    sfl = _slot(data["sf_left"])
    sfr = _slot(data["sf_right"])

    final_box = (
        '<div class="final-col">'
        '<div class="fl">🏆 Final</div>'
        + _md_game(data["final"], hl=True)
        + '<div style="height:24px;"></div>'
        '<div class="fl" style="color:#888;">3er Puesto</div>' + _md_game(data["third"]) + "</div>"
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
.sc{{font-weight:bold;color:#f5b020}}
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
.fl{{font-size:12px;font-weight:bold;color:#f5b020;text-align:center;margin-bottom:4px}}
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
  <div class="round">{r16l}</div>
  {_conn_col(2, "cl")}
  <div class="round">{qfl}</div>
  {_conn_col(1, "cl")}
  <div class="round">{sfl}</div>
  <div class="conns"><div class="hl"></div></div>
  {final_box}
  <div class="conns"><div class="hl"></div></div>
  <div class="round">{sfr}</div>
  {_conn_col(1, "cr")}
  <div class="round">{qfr}</div>
  {_conn_col(2, "cr")}
  <div class="round">{r16r}</div>
  {_conn_col(4, "cr")}
  <div class="round">{r32r}</div>
</div>
</div>
</body></html>"""


def _render_bracket(all_matches: list[dict], simulated: dict):
    st.markdown("### Fase Eliminatoria")
    st.caption("El bracket se actualiza automaticamente con los resultados de los partidos.")

    data = _resolve_bracket_data(all_matches, simulated)
    html = _build_bracket_html(data)
    components.html(html, height=620, scrolling=True)

    ko = _knockout_matches(all_matches)
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

st.markdown(eyebrow("Mundial 2026 · Fase de grupos"), unsafe_allow_html=True)
st.markdown(page_title("FIFA World Cup 2026"), unsafe_allow_html=True)
st.markdown(
    '<p style="color:#6b7382;font-size:0.88rem;margin:-16px 0 16px 0;">'
    "Estados Unidos · Mexico · Canada  |  11 junio — 19 julio 2026</p>",
    unsafe_allow_html=True,
)

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
_render_bracket(all_matches, simulated)

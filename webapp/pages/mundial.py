"""FIFA World Cup 2026 — Groups, standings, and knockout bracket."""

from nicegui import ui

from webapp.data import load_wc_matches
from webapp.theme import render_mini_strip

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
    "England": "🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f",
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
    "Scotland": "🏴\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f",
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

_TEAM_TO_GROUP = {}
for _letter, _teams in WC_GROUPS.items():
    for _t in _teams:
        _TEAM_TO_GROUP[_t] = _letter


def _flag(team: str) -> str:
    return FLAGS.get(team, "")


def _code(team: str) -> str:
    return CODES.get(team, team[:3].upper())


def _team_label(team: str) -> str:
    if not team:
        return "---"
    return f"{_flag(team)} {_code(team)}"


def _group_matches(all_matches: list[dict], teams: list[str]) -> list[dict]:
    s = set(teams)
    return [m for m in all_matches if m["home_team"] in s and m["away_team"] in s]


def _knockout_matches(all_matches: list[dict]) -> list[dict]:
    return [
        m
        for m in all_matches
        if _TEAM_TO_GROUP.get(m["home_team"]) != _TEAM_TO_GROUP.get(m["away_team"])
    ]


def _calc_standings(teams: list[str], matches: list[dict]) -> list[dict]:
    stats = {t: {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0} for t in teams}
    for m in matches:
        home, away = m["home_team"], m["away_team"]
        if m["ft_result"] is None:
            continue
        hg, ag = m["ft_home_goals"], m["ft_away_goals"]
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


# ── Bracket logic ──

R32_LEFT = [
    [("2A", "2B"), ("1F", "2C")],
    [("1E", "3°"), ("1G", "3°")],
    [("2K", "2L"), ("1H", "2J")],
    [("1D", "3°"), ("1I", "3°")],
]

R32_RIGHT = [
    [("1C", "2F"), ("2E", "2G")],
    [("1A", "3°"), ("1L", "3°")],
    [("1J", "2H"), ("2D", "2I")],
    [("1B", "3°"), ("1K", "3°")],
]


def _resolve_bracket(all_matches: list[dict]) -> dict:
    pos_map: dict[str, str] = {}
    for letter, teams in WC_GROUPS.items():
        gm = _group_matches(all_matches, teams)
        standings = _calc_standings(teams, gm)
        for i, row in enumerate(standings):
            pos_map[f"{i + 1}{letter}"] = row["team"]

    ko = _knockout_matches(all_matches)

    def _by_date(lo, hi):
        return [m for m in ko if lo <= m["match_date"] <= hi]

    r32_pool = [m for m in ko if m["match_date"] <= "2026-07-03"]
    r16_pool = _by_date("2026-07-04", "2026-07-08")
    qf_pool = _by_date("2026-07-09", "2026-07-12")
    sf_pool = _by_date("2026-07-13", "2026-07-16")
    final_pool = [m for m in ko if m["match_date"] >= "2026-07-17"]

    def _find(pool, t1, t2):
        if not t1 or not t2:
            return None
        pair = {t1, t2}
        for m in pool:
            if {m["home_team"], m["away_team"]} == pair:
                return m
        return None

    def _find_for(pool, team):
        if not team:
            return None
        for m in pool:
            if team in (m["home_team"], m["away_team"]):
                return m
        return None

    def _winner(match, next_pool):
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

    r16_left = []
    for pair in r32_left:
        w1 = _winner(pair[0]["match"], r16_pool)
        w2 = _winner(pair[1]["match"], r16_pool)
        r16_left.append({"t1": w1, "t2": w2, "match": _find(r16_pool, w1, w2)})

    r16_right = []
    for pair in r32_right:
        w1 = _winner(pair[0]["match"], r16_pool)
        w2 = _winner(pair[1]["match"], r16_pool)
        r16_right.append({"t1": w1, "t2": w2, "match": _find(r16_pool, w1, w2)})

    qf_left = []
    for i in range(0, 4, 2):
        w1 = _winner(r16_left[i]["match"], qf_pool)
        w2 = _winner(r16_left[i + 1]["match"], qf_pool)
        qf_left.append({"t1": w1, "t2": w2, "match": _find(qf_pool, w1, w2)})

    qf_right = []
    for i in range(0, 4, 2):
        w1 = _winner(r16_right[i]["match"], qf_pool)
        w2 = _winner(r16_right[i + 1]["match"], qf_pool)
        qf_right.append({"t1": w1, "t2": w2, "match": _find(qf_pool, w1, w2)})

    sf_lw1 = _winner(qf_left[0]["match"], sf_pool)
    sf_lw2 = _winner(qf_left[1]["match"], sf_pool)
    sf_left = {"t1": sf_lw1, "t2": sf_lw2, "match": _find(sf_pool, sf_lw1, sf_lw2)}

    sf_rw1 = _winner(qf_right[0]["match"], sf_pool)
    sf_rw2 = _winner(qf_right[1]["match"], sf_pool)
    sf_right = {"t1": sf_rw1, "t2": sf_rw2, "match": _find(sf_pool, sf_rw1, sf_rw2)}

    actual_final = max(final_pool, key=lambda m: m["match_date"]) if final_pool else None
    final_only = [actual_final] if actual_final else []

    final_t1 = _winner(sf_left["match"], final_only)
    final_t2 = _winner(sf_right["match"], final_only)
    final = {"t1": final_t1, "t2": final_t2, "match": _find(final_pool, final_t1, final_t2)}

    third_t1 = _loser(sf_left["match"], final_only)
    third_t2 = _loser(sf_right["match"], final_only)
    third = {"t1": third_t1, "t2": third_t2, "match": _find(final_pool, third_t1, third_t2)}

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


def _bracket_html(data: dict) -> str:
    def _game(t1, t2, s1="", s2="", hl=False):
        border = "border-color:var(--flame);" if hl else ""
        return (
            f'<div class="bk-game" style="{border}">'
            f'<div class="bk-tr"><span>{t1}</span><span class="bk-sc">{s1}</span></div>'
            f'<div class="bk-tr"><span>{t2}</span><span class="bk-sc">{s2}</span></div>'
            f"</div>"
        )

    def _md_game(md, hl=False):
        t1 = _team_label(md["t1"]) if md else "---"
        t2 = _team_label(md["t2"]) if md else "---"
        s1 = s2 = ""
        if md and md.get("match") and md["match"]["ft_home_goals"] is not None:
            m = md["match"]
            if m["home_team"] == md["t1"]:
                s1, s2 = str(m["ft_home_goals"]), str(m["ft_away_goals"])
            else:
                s1, s2 = str(m["ft_away_goals"]), str(m["ft_home_goals"])
        return _game(t1, t2, s1, s2, hl)

    def _pair(pair):
        items = "".join(_md_game(md) for md in pair)
        return f'<div class="bk-pair">{items}</div>'

    def _slot(md):
        return f'<div class="bk-slot">{_md_game(md)}</div>'

    def _conns(n, cls):
        return '<div class="bk-conns">' + f'<div class="{cls}"></div>' * n + "</div>"

    r32l = "".join(_pair(p) for p in data["r32_left"])
    r32r = "".join(_pair(p) for p in data["r32_right"])
    r16l = "".join(_slot(md) for md in data["r16_left"])
    r16r = "".join(_slot(md) for md in data["r16_right"])
    qfl = "".join(_slot(md) for md in data["qf_left"])
    qfr = "".join(_slot(md) for md in data["qf_right"])
    sfl = _slot(data["sf_left"])
    sfr = _slot(data["sf_right"])

    final_box = (
        '<div class="bk-final">'
        '<div class="bk-fl">Final</div>'
        + _md_game(data["final"], hl=True)
        + '<div style="height:20px"></div>'
        '<div class="bk-fl" style="color:var(--text-3)">3er Puesto</div>'
        + _md_game(data["third"])
        + "</div>"
    )

    labels = (
        '<div class="bk-labels">'
        "<span>16avos</span><span>8avos</span><span>4tos</span><span>Semis</span>"
        '<span style="min-width:120px">FINAL</span>'
        "<span>Semis</span><span>4tos</span><span>8avos</span><span>16avos</span>"
        "</div>"
    )

    return (
        f'<div class="bracket-wrap">{labels}'
        f'<div class="bk-bracket">'
        f'<div class="bk-round">{r32l}</div>'
        f"{_conns(4, 'bk-cl')}"
        f'<div class="bk-round">{r16l}</div>'
        f"{_conns(2, 'bk-cl')}"
        f'<div class="bk-round">{qfl}</div>'
        f"{_conns(1, 'bk-cl')}"
        f'<div class="bk-round">{sfl}</div>'
        f'<div class="bk-conns"><div class="bk-hl"></div></div>'
        f"{final_box}"
        f'<div class="bk-conns"><div class="bk-hl"></div></div>'
        f'<div class="bk-round">{sfr}</div>'
        f"{_conns(1, 'bk-cr')}"
        f'<div class="bk-round">{qfr}</div>'
        f"{_conns(2, 'bk-cr')}"
        f'<div class="bk-round">{r16r}</div>'
        f"{_conns(4, 'bk-cr')}"
        f'<div class="bk-round">{r32r}</div>'
        f"</div></div>"
    )


def render():
    render_mini_strip("FIFA World Cup 2026", "Mundial 2026", "trophy")
    ui.html(
        '<div style="color:var(--text-3);font-size:12px;margin:-4px 0 16px">'
        "Estados Unidos · Mexico · Canada | 11 junio — 19 julio 2026</div>"
    )

    try:
        all_matches = load_wc_matches()
    except Exception:
        all_matches = []

    played = sum(1 for m in all_matches if m["ft_result"] is not None)
    total = len(all_matches)

    ui.html(
        f'<div class="kpi-row">'
        f'<div class="kpi"><div class="kpi-val">48</div><div class="kpi-lbl">Equipos</div></div>'
        f'<div class="kpi"><div class="kpi-val">{total}</div><div class="kpi-lbl">Partidos</div></div>'
        f'<div class="kpi"><div class="kpi-val" style="color:var(--hit)">{played}</div><div class="kpi-lbl">Jugados</div></div>'
        f"</div>"
    )

    # Group cards
    ui.html(
        '<h2 style="font-size:15px;font-weight:700;margin:20px 0 12px;letter-spacing:-0.01em">Fase de Grupos</h2>'
    )
    ui.html(
        '<div style="font-size:11px;color:var(--text-3);margin-bottom:12px">'
        "Verde = clasifica directo (1° y 2°) · Amarillo = posible clasificacion (mejor 3°)</div>"
    )

    groups_html = '<div class="wc-groups">'
    for letter, teams in WC_GROUPS.items():
        gm = _group_matches(all_matches, teams)
        standings = _calc_standings(teams, gm)
        groups_html += f'<div class="wc-group"><div class="wc-group-title">Grupo {letter}</div>'
        for i, row in enumerate(standings):
            cls = "q1" if i < 2 else ("q3" if i == 2 else "")
            dif = f"+{row['DIF']}" if row["DIF"] > 0 else str(row["DIF"])
            groups_html += (
                f'<div class="wc-row {cls}">'
                f'<span class="wc-team">{_flag(row["team"])} {_code(row["team"])}</span>'
                f'<span class="wc-pts"><strong>{row["Pts"]}</strong>'
                f"<small>{row['PJ']}j {dif}</small></span>"
                f"</div>"
            )
        groups_html += "</div>"
    groups_html += "</div>"
    ui.html(groups_html)

    # Knockout matches list
    ko = _knockout_matches(all_matches)
    if ko:
        ui.html(
            '<h2 style="font-size:15px;font-weight:700;margin:24px 0 12px;letter-spacing:-0.01em">Fase Eliminatoria</h2>'
        )
        ui.html(
            '<div style="font-size:11px;color:var(--text-3);margin-bottom:12px">El bracket se actualiza automaticamente con resultados.</div>'
        )

        data = _resolve_bracket(all_matches)
        ui.html(_bracket_html(data))

        # Match list below bracket
        ko_html = '<div class="match-list" style="margin-top:16px">'
        ko_html += '<div class="ml-head"><h2>Partidos eliminatoria</h2></div>'
        for m in ko:
            home, away = m["home_team"], m["away_team"]
            if m["ft_result"] is not None:
                score_str = f"{m['ft_home_goals']} – {m['ft_away_goals']}"
            else:
                score_str = "vs"
            ko_html += (
                f'<div class="tp-row">'
                f'<span class="tp-date">{m["match_date"]}</span>'
                f'<span class="tp-match">{_flag(home)} {_code(home)} {score_str} {_code(away)} {_flag(away)}</span>'
                f"<span></span><span></span><span></span>"
                f"</div>"
            )
        ko_html += "</div>"
        ui.html(ko_html)

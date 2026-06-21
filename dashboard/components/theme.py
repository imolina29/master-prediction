import streamlit as st

GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800"
    "&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700"
    "&family=DM+Mono:wght@400;500&display=swap"
)

FOOTBALL_CSS = f"""
<style>
@import url('{GOOGLE_FONTS}');

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; }}

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {{
    font-family: 'DM Sans', system-ui, sans-serif !important;
}}
.stApp {{ background: #07090c; }}
.stMainBlockContainer {{ padding-top: 1.5rem !important; }}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: #1c1c1c; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: #333; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: #0a0d11;
    border-right: 1px solid rgba(255,255,255,0.06);
}}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p {{ color: #6b7382; }}

/* ── Sidebar nav ── */
[data-testid="stSidebarNav"] {{ padding-top: 0.5rem; }}

[data-testid="stSidebarNav"] a {{
    border-radius: 11px !important;
    margin: 2px 8px !important;
    padding: 0.5rem 0.9rem !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid transparent !important;
}}
[data-testid="stSidebarNav"] a:hover {{
    background: rgba(22,196,127,0.04) !important;
    border-color: rgba(22,196,127,0.10) !important;
}}
[data-testid="stSidebarNav"] a[aria-selected="true"] {{
    background: rgba(22,196,127,0.08) !important;
    border-color: rgba(22,196,127,0.18) !important;
}}
[data-testid="stSidebarNav"] a span {{
    color: #6b7382 !important; font-size: 0.86rem !important; font-weight: 500 !important;
}}
[data-testid="stSidebarNav"] a[aria-selected="true"] span {{
    color: #eef1f5 !important; font-weight: 600 !important;
}}

/* ── Sidebar section headers ── */
[data-testid="stSidebarNav"] h2 {{
    font-size: 0.66rem !important; text-transform: uppercase !important;
    letter-spacing: 0.10em !important; color: #8b94a2 !important;
    border-bottom: none !important; padding: 0.8rem 0 0.2rem 0.9rem !important;
    margin: 0 !important; font-family: 'DM Sans', sans-serif !important;
}}

/* ── User menu popover ── */
[data-testid="stPopover"] > button {{
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 11px !important; color: #8b94a2 !important;
    font-size: 0.85rem !important; padding: 0.4rem 0.8rem !important;
    transition: all 0.2s !important;
}}
[data-testid="stPopover"] > button:hover {{
    background: rgba(22,196,127,0.04) !important;
    border-color: rgba(22,196,127,0.15) !important;
}}
[data-testid="stPopoverBody"] {{
    background: #0a0d11 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
}}

/* ── Metric cards ── */
[data-testid="stMetric"] {{
    background: #0c1015;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 20px 24px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}
[data-testid="stMetric"]:hover {{
    border-color: rgba(22,196,127,0.22);
    transform: translateY(-2px);
    box-shadow: 0 8px 26px rgba(0,0,0,0.3);
}}
[data-testid="stMetricLabel"] {{
    color: #8b94a2 !important; font-size: 0.76rem !important;
    text-transform: uppercase !important; letter-spacing: 0.07em !important;
    font-weight: 600 !important;
}}
[data-testid="stMetricValue"] {{
    color: #eef1f5 !important; font-weight: 800 !important; letter-spacing: -0.03em !important;
    font-family: 'Sora', sans-serif !important;
}}
[data-testid="stMetricDelta"] svg {{ display: inline; }}

/* ── Headings ── */
h1 {{
    color: #eef1f5 !important; font-weight: 800 !important;
    letter-spacing: -0.04em !important; font-family: 'Sora', sans-serif !important;
}}
h2 {{
    color: #eef1f5 !important; font-weight: 700 !important;
    letter-spacing: -0.02em !important; font-family: 'Sora', sans-serif !important;
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
    padding-bottom: 8px;
}}
h3 {{ color: #c2cad6 !important; font-weight: 600 !important; font-family: 'Sora', sans-serif !important; }}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {{
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    overflow: hidden;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    background: rgba(255,255,255,0.01);
    transition: border-color 0.2s;
}}
[data-testid="stExpander"]:hover {{ border-color: rgba(255,255,255,0.10); }}
[data-testid="stExpander"] summary {{ color: #c2cad6 !important; }}

/* ── Alerts ── */
[data-testid="stAlert"] {{
    border-radius: 11px;
    border: 1px solid rgba(255,255,255,0.06) !important;
    background: rgba(255,255,255,0.015) !important;
}}

/* ── Divider ── */
hr {{ border-color: rgba(255,255,255,0.06) !important; }}

/* ── Selectbox / inputs ── */
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stNumberInput"] label {{
    color: #8b94a2 !important; font-weight: 600 !important;
    font-size: 0.82rem !important; text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}}

/* ── Tabs ── */
[data-testid="stTabs"] button[aria-selected="true"] {{
    border-bottom: 2px solid #16c47f !important;
    color: #eef1f5 !important; font-weight: 600 !important;
}}
[data-testid="stTabs"] button {{
    color: #6b7382 !important; transition: color 0.2s !important;
}}
[data-testid="stTabs"] button:hover {{ color: #c2cad6 !important; }}

/* ── Buttons ── */
[data-testid="stButton"] button {{
    background: rgba(22,196,127,0.06) !important;
    border: 1px solid rgba(22,196,127,0.12) !important;
    color: #c2cad6 !important; border-radius: 11px !important;
    font-weight: 500 !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}}
[data-testid="stButton"] button:hover {{
    background: rgba(22,196,127,0.12) !important;
    border-color: rgba(22,196,127,0.25) !important;
    color: #eef1f5 !important; transform: translateY(-1px) !important;
}}

/* ── Plotly transparent bg ── */
.js-plotly-plot .plotly .main-svg {{ background: transparent !important; }}

/* ── Spinner ── */
[data-testid="stSpinner"] {{ color: #16c47f !important; }}

/* ── Captions ── */
[data-testid="stCaptionContainer"] {{ color: #6b7382 !important; }}

/* ── Custom stat card ── */
.mp-stat-card {{
    background: #0c1015;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}
.mp-stat-card:hover {{
    border-color: rgba(22,196,127,0.22);
    transform: translateY(-2px);
    box-shadow: 0 8px 26px rgba(0,0,0,0.3);
}}
.mp-stat-card.featured {{
    border-color: rgba(22,196,127,0.22);
    background: linear-gradient(160deg, #122a20, #0b1411);
}}
.mp-stat-card h4 {{
    color: #8b94a2 !important; font-size: 0.68rem;
    text-transform: uppercase; letter-spacing: 0.10em;
    font-weight: 600; margin: 0 0 0.5rem 0;
    font-family: 'DM Sans', sans-serif;
}}
.mp-stat-card .value {{
    color: #eef1f5; font-size: 2rem; font-weight: 800;
    letter-spacing: -0.02em; margin: 0; line-height: 1.2;
    font-family: 'Sora', sans-serif;
}}
.mp-stat-card .sub {{
    color: #6b7382; font-size: 0.76rem; margin: 0.3rem 0 0 0;
}}
.mp-stat-card .delta {{
    display: inline-block; padding: 2px 8px; border-radius: 100px;
    font-size: 0.72rem; font-weight: 600;
    background: rgba(22,196,127,0.12); color: #5fe0a6;
    margin-left: 6px;
}}
.mp-stat-card .progress-bar {{
    height: 4px; background: rgba(255,255,255,0.04);
    border-radius: 2px; margin-top: 10px; overflow: hidden;
}}
.mp-stat-card .progress-fill {{
    height: 100%; border-radius: 2px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}}

/* ── Eyebrow label ── */
.mp-eyebrow {{
    font-size: 12px; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: #16c47f;
    margin-bottom: 4px;
    font-family: 'DM Sans', sans-serif;
}}

/* ── Page title ── */
.mp-page-title {{
    font-size: 32px; font-weight: 800; color: #eef1f5;
    letter-spacing: -0.02em; margin: 0 0 4px 0;
    font-family: 'Sora', sans-serif;
}}
.mp-page-subtitle {{
    font-size: 14px; color: #8b94a2; margin: 0 0 24px 0;
}}

/* ── Section header ── */
.mp-section-header {{
    display: flex; align-items: center; gap: 0.6rem;
    margin: 2rem 0 1rem 0;
}}
.mp-section-header .icon {{ font-size: 1rem; }}
.mp-section-header .title {{
    color: #c2cad6; font-size: 0.85rem; font-weight: 600;
    letter-spacing: -0.01em; font-family: 'Sora', sans-serif;
}}
.mp-section-header .line {{
    flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(22,196,127,0.15), transparent);
}}

/* ── Confidence badges ── */
.mp-badge-alta {{
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(22,196,127,0.13); color: #5fe0a6;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em;
    border: 1px solid rgba(22,196,127,0.22);
}}
.mp-badge-media {{
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(245,176,32,0.14); color: #f5c451;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em;
    border: 1px solid rgba(245,176,32,0.22);
}}
.mp-badge-baja {{
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(236,55,80,0.13); color: #ff7d92;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em;
    border: 1px solid rgba(236,55,80,0.22);
}}

/* ── Prediction card ── */
.mp-pred-card {{
    background: #0c1015;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}
.mp-pred-card:hover {{
    border-color: rgba(22,196,127,0.22);
    box-shadow: 0 8px 26px rgba(0,0,0,0.3);
}}
.mp-pred-card .match-header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 4px;
}}
.mp-pred-card .teams {{
    color: #eef1f5; font-weight: 700; font-size: 15px;
    letter-spacing: -0.01em; font-family: 'Sora', sans-serif;
}}
.mp-pred-card .meta {{
    color: #6b7382; font-size: 0.78rem; margin-bottom: 14px;
}}
.mp-pred-card .prediction-label {{
    color: #8b94a2; font-size: 0.82rem; margin-bottom: 10px;
}}
.mp-pred-card .prediction-label strong {{
    color: #eef1f5;
}}

/* ── Probability bars ── */
.mp-prob-row {{
    display: flex; align-items: center; gap: 10px; margin: 5px 0;
}}
.mp-prob-row .label {{
    color: #8b94a2; font-size: 0.8rem; width: 65px; font-weight: 400;
}}
.mp-prob-row .label.active {{
    color: #eef1f5; font-weight: 600;
}}
.mp-prob-row .bar-bg {{
    flex: 1; height: 7px; background: rgba(255,255,255,0.04);
    border-radius: 4px; overflow: hidden;
}}
.mp-prob-row .bar-fill {{
    height: 100%; border-radius: 4px;
    transition: width 0.5s ease;
}}
.mp-prob-row .bar-fill.active {{ background: #16c47f; }}
.mp-prob-row .bar-fill.inactive {{ background: rgba(255,255,255,0.08); }}
.mp-prob-row .pct {{
    color: #8b94a2; font-size: 0.8rem; width: 42px; text-align: right;
    font-weight: 400; font-family: 'DM Mono', monospace;
}}
.mp-prob-row .pct.active {{
    color: #eef1f5; font-weight: 600;
}}

/* ── Extras row ── */
.mp-extras {{
    color: #6b7382; font-size: 0.78rem; margin-top: 12px; padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.04);
}}
.mp-extras strong {{ color: #c2cad6; }}

/* ── Confidence distribution bar ── */
.mp-conf-dist {{
    display: flex; height: 8px; border-radius: 4px; overflow: hidden;
    background: rgba(255,255,255,0.04); margin-top: 8px;
}}
.mp-conf-dist .seg {{
    height: 100%; transition: width 0.5s ease;
}}

/* ── Filter pills ── */
.mp-filter-pills {{
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;
}}
.mp-filter-pill {{
    padding: 6px 16px; border-radius: 100px;
    font-size: 0.82rem; font-weight: 500;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    color: #8b94a2; cursor: pointer;
    transition: all 0.2s;
}}
.mp-filter-pill.active {{
    background: rgba(22,196,127,0.10);
    border-color: rgba(22,196,127,0.25);
    color: #5fe0a6;
}}
.mp-filter-pill .count {{
    margin-left: 4px; opacity: 0.6;
}}

/* ── Hero (home) ── */
.mp-hero {{
    text-align: center; padding: 2.5rem 0 2rem;
    background: radial-gradient(120% 90% at 50% 0%, rgba(22,196,127,0.06) 0%, transparent 60%);
    border-radius: 18px; margin-bottom: 1.5rem;
}}
.mp-hero h1 {{
    font-size: 2.6rem !important; margin: 0 !important;
    letter-spacing: -0.03em !important;
    font-family: 'Sora', sans-serif !important;
}}
.mp-hero .tagline {{
    color: #16c47f; font-size: 0.78rem; margin-top: 8px;
    letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;
    font-family: 'DM Sans', sans-serif;
}}

/* ── Result badges ── */
.badge-win {{
    background: rgba(22,196,127,0.12); color: #5fe0a6;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.82rem; border: 1px solid rgba(22,196,127,0.22);
}}
.badge-loss {{
    background: rgba(236,55,80,0.12); color: #ff7d92;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.82rem; border: 1px solid rgba(236,55,80,0.22);
}}
.badge-pending {{
    background: rgba(245,176,32,0.10); color: #f5c451;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.82rem; border: 1px solid rgba(245,176,32,0.18);
}}

/* ── Comparator bars ── */
.mp-compare-bar {{
    display: flex; align-items: center; gap: 8px; margin: 8px 0;
}}
.mp-compare-bar .team-val {{
    font-size: 0.85rem; font-weight: 600; width: 40px; text-align: right;
    font-family: 'DM Mono', monospace;
}}
.mp-compare-bar .bar-track {{
    flex: 1; height: 6px; background: rgba(255,255,255,0.04);
    border-radius: 3px; overflow: hidden; position: relative;
}}
.mp-compare-bar .bar-a {{
    position: absolute; left: 0; height: 100%;
    background: #16c47f; border-radius: 3px;
}}
.mp-compare-bar .bar-b {{
    position: absolute; right: 0; height: 100%;
    background: #7fb0ff; border-radius: 3px;
}}
.mp-compare-bar .metric-label {{
    font-size: 0.78rem; color: #8b94a2; width: 70px; text-align: center;
}}
</style>
"""


def apply_theme():
    st.markdown(FOOTBALL_CSS, unsafe_allow_html=True)


def eyebrow(text: str) -> str:
    return f'<div class="mp-eyebrow">{text}</div>'


def page_title(title: str, subtitle: str = "") -> str:
    sub = f'<p class="mp-page-subtitle">{subtitle}</p>' if subtitle else ""
    return f'<div class="mp-page-title">{title}</div>{sub}'


def stat_card(
    title: str,
    value: str,
    subtitle: str = "",
    delta: str = "",
    progress: float | None = None,
    featured: bool = False,
    color: str = "#16c47f",
) -> str:
    cls = "mp-stat-card featured" if featured else "mp-stat-card"
    sub_html = f'<p class="sub">{subtitle}</p>' if subtitle else ""
    delta_html = f'<span class="delta">{delta}</span>' if delta else ""
    prog_html = ""
    if progress is not None:
        prog_html = (
            f'<div class="progress-bar">'
            f'<div class="progress-fill" style="width:{progress}%;background:{color};"></div>'
            f"</div>"
        )
    return (
        f'<div class="{cls}">'
        f"<h4>{title}</h4>"
        f'<p class="value">{value}{delta_html}</p>'
        f"{sub_html}{prog_html}"
        f"</div>"
    )


def section_header(icon: str, title: str) -> str:
    return (
        f'<div class="mp-section-header">'
        f'<span class="icon">{icon}</span>'
        f'<span class="title">{title}</span>'
        f'<span class="line"></span>'
        f"</div>"
    )


def page_header(icon: str, title: str) -> str:
    return (
        f'<div style="margin-bottom:1rem;">'
        f'<span style="font-size:1.4rem;font-weight:700;'
        f"color:#eef1f5;letter-spacing:-0.02em;"
        f"font-family:'Sora',sans-serif;\">"
        f"{icon} {title}</span></div>"
    )


def section_tag(label: str) -> str:
    return (
        f'<span style="display:inline-block;padding:4px 12px;border-radius:100px;'
        f"font-size:0.7rem;font-weight:600;letter-spacing:0.06em;"
        f"text-transform:uppercase;color:#16c47f;"
        f"background:rgba(22,196,127,0.06);border:1px solid rgba(22,196,127,0.12);"
        f'margin-bottom:8px;">{label}</span>'
    )


def confidence_badge(level: str) -> str:
    dots = {"alta": "#16c47f", "media": "#f5b020", "baja": "#ec3750"}
    dot = dots.get(level, "#6b7382")
    cls = f"mp-badge-{level}" if level in ("alta", "media", "baja") else "mp-badge-baja"
    return (
        f'<span class="{cls}">'
        f'<span style="width:6px;height:6px;border-radius:50%;background:{dot};display:inline-block;"></span>'
        f"{level}</span>"
    )


def prediction_card(
    home: str,
    away: str,
    date: str,
    league: str,
    prob_h: float,
    prob_d: float,
    prob_a: float,
    predicted: str,
    confidence: str,
    prob_over25: float | None = None,
    prob_btts: float | None = None,
) -> str:
    result_labels = {"H": "Local", "D": "Empate", "A": "Visitante"}
    pred_label = result_labels.get(predicted, "?")

    def _bar(label, prob, is_active):
        pct = prob * 100
        cls_l = "label active" if is_active else "label"
        cls_f = "bar-fill active" if is_active else "bar-fill inactive"
        cls_p = "pct active" if is_active else "pct"
        return (
            f'<div class="mp-prob-row">'
            f'<span class="{cls_l}">{label}</span>'
            f'<div class="bar-bg"><div class="{cls_f}" style="width:{pct:.0f}%;"></div></div>'
            f'<span class="{cls_p}">{prob:.0%}</span>'
            f"</div>"
        )

    bars = (
        _bar("Local", prob_h, predicted == "H")
        + _bar("Empate", prob_d, predicted == "D")
        + _bar("Visitante", prob_a, predicted == "A")
    )

    extras = []
    if prob_over25 is not None:
        extras.append(f"Over 2.5: <strong>{prob_over25:.0%}</strong>")
    if prob_btts is not None:
        extras.append(f"BTTS: <strong>{prob_btts:.0%}</strong>")
    extras_html = f'<div class="mp-extras">{"  ·  ".join(extras)}</div>' if extras else ""

    badge = confidence_badge(confidence)

    return (
        f'<div class="mp-pred-card">'
        f'<div class="match-header">'
        f'<span class="teams">{home} vs {away}</span>'
        f"{badge}"
        f"</div>"
        f'<div class="meta">📅 {date}  ·  {league}</div>'
        f'<div class="prediction-label">Prediccion: <strong>{pred_label}</strong></div>'
        f"{bars}{extras_html}"
        f"</div>"
    )


def confidence_distribution(alta: int, media: int, baja: int) -> str:
    total = alta + media + baja
    if total == 0:
        return ""
    pa = alta / total * 100
    pm = media / total * 100
    pb = baja / total * 100
    return (
        f'<div style="margin:16px 0;">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
        f'<span style="font-size:0.78rem;color:#5fe0a6;font-weight:600;">Alta {alta}</span>'
        f'<span style="font-size:0.78rem;color:#f5c451;font-weight:600;">Media {media}</span>'
        f'<span style="font-size:0.78rem;color:#ff7d92;font-weight:600;">Baja {baja}</span>'
        f"</div>"
        f'<div class="mp-conf-dist">'
        f'<div class="seg" style="width:{pa:.0f}%;background:#16c47f;"></div>'
        f'<div class="seg" style="width:{pm:.0f}%;background:#f5b020;"></div>'
        f'<div class="seg" style="width:{pb:.0f}%;background:#ec3750;"></div>'
        f"</div>"
        f"</div>"
    )


def confidence_gauge(value: float, label: str = "") -> str:
    pct = max(0, min(100, value * 100))
    if pct >= 65:
        color = "#16c47f"
    elif pct >= 45:
        color = "#f5b020"
    else:
        color = "#ec3750"
    label_html = f'<span style="color:#8b94a2;font-size:0.78rem;">{label}</span>' if label else ""
    return (
        f'<div style="display:inline-block;width:100%;">'
        f"{label_html}"
        f'<div style="height:4px;background:rgba(255,255,255,0.04);border-radius:2px;overflow:hidden;margin-top:4px;">'
        f'<div style="height:100%;border-radius:2px;width:{pct:.0f}%;background:{color};transition:width 0.5s ease;"></div>'
        f"</div></div>"
    )

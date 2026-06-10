import streamlit as st

FOOTBALL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
.stApp { background: #070707; }
.stMainBlockContainer { padding-top: 1.5rem !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1c1c1c; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #333; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #060606;
    border-right: 1px solid rgba(255,255,255,0.03);
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p { color: #666; }

/* ── Sidebar nav ── */
[data-testid="stSidebarNav"] { padding-top: 0.5rem; }

[data-testid="stSidebarNav"] a {
    border-radius: 10px !important;
    margin: 2px 8px !important;
    padding: 0.5rem 0.9rem !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid transparent !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(76,175,80,0.04) !important;
    border-color: rgba(76,175,80,0.08) !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background: rgba(76,175,80,0.08) !important;
    border-color: rgba(76,175,80,0.15) !important;
}
[data-testid="stSidebarNav"] a span {
    color: #666 !important; font-size: 0.86rem !important; font-weight: 500 !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] span {
    color: #fff !important; font-weight: 600 !important;
}

/* ── Sidebar section headers ── */
[data-testid="stSidebarNav"] h2 {
    font-size: 0.66rem !important; text-transform: uppercase !important;
    letter-spacing: 0.1em !important; color: #333 !important;
    border-bottom: none !important; padding: 0.8rem 0 0.2rem 0.9rem !important;
    margin: 0 !important;
}

/* ── User menu popover ── */
[data-testid="stPopover"] > button {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 10px !important; color: #888 !important;
    font-size: 0.85rem !important; padding: 0.4rem 0.8rem !important;
    transition: all 0.2s !important;
}
[data-testid="stPopover"] > button:hover {
    background: rgba(76,175,80,0.04) !important;
    border-color: rgba(76,175,80,0.12) !important;
}
[data-testid="stPopoverBody"] {
    background: #0a0a0a !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 12px !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(255,255,255,0.025) 0%, rgba(255,255,255,0.008) 100%);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 20px 24px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
[data-testid="stMetric"]:hover {
    border-color: rgba(76,175,80,0.15);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
[data-testid="stMetricLabel"] {
    color: #555 !important; font-size: 0.76rem !important;
    text-transform: uppercase !important; letter-spacing: 0.07em !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    color: #fff !important; font-weight: 800 !important; letter-spacing: -0.03em !important;
}
[data-testid="stMetricDelta"] svg { display: inline; }

/* ── Headings ── */
h1 {
    color: #fff !important; font-weight: 800 !important;
    letter-spacing: -0.04em !important;
}
h2 {
    color: #fff !important; font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    border-bottom: 1px solid rgba(255,255,255,0.04) !important;
    padding-bottom: 8px;
}
h3 { color: #ccc !important; font-weight: 600 !important; }

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
    overflow: hidden;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 14px;
    background: rgba(255,255,255,0.01);
    transition: border-color 0.2s;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(255,255,255,0.08);
}
[data-testid="stExpander"] summary { color: #999 !important; }

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.04) !important;
    background: rgba(255,255,255,0.015) !important;
}

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.04) !important; }

/* ── Selectbox / inputs ── */
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stNumberInput"] label {
    color: #666 !important; font-weight: 500 !important;
    font-size: 0.82rem !important; text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] button[aria-selected="true"] {
    border-bottom: 2px solid #4CAF50 !important;
    color: #fff !important; font-weight: 600 !important;
}
[data-testid="stTabs"] button {
    color: #555 !important; transition: color 0.2s !important;
}
[data-testid="stTabs"] button:hover { color: #aaa !important; }

/* ── Buttons ── */
[data-testid="stButton"] button {
    background: rgba(76,175,80,0.05) !important;
    border: 1px solid rgba(76,175,80,0.1) !important;
    color: #bbb !important; border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
[data-testid="stButton"] button:hover {
    background: rgba(76,175,80,0.1) !important;
    border-color: rgba(76,175,80,0.2) !important;
    color: #fff !important; transform: translateY(-1px) !important;
}

/* ── Plotly transparent bg ── */
.js-plotly-plot .plotly .main-svg { background: transparent !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #4CAF50 !important; }

/* ── Captions ── */
[data-testid="stCaptionContainer"] { color: #444 !important; }

/* ── Custom stat card ── */
.stat-card {
    background: linear-gradient(145deg, rgba(255,255,255,0.025) 0%, rgba(255,255,255,0.008) 100%);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.stat-card:hover {
    border-color: rgba(76,175,80,0.15);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}
.stat-card h4 {
    color: #555 !important; font-size: 0.7rem;
    text-transform: uppercase; letter-spacing: 0.08em;
    font-weight: 600; margin: 0 0 0.5rem 0;
}
.stat-card .value {
    color: #fff; font-size: 1.8rem; font-weight: 800;
    letter-spacing: -0.03em; margin: 0; line-height: 1.2;
}
.stat-card .sub {
    color: #444; font-size: 0.76rem; margin: 0.3rem 0 0 0;
}

/* ── Result badges ── */
.badge-win {
    background: rgba(76,175,80,0.1); color: #4CAF50;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.82rem; border: 1px solid rgba(76,175,80,0.15);
}
.badge-loss {
    background: rgba(229,57,53,0.1); color: #EF5350;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.82rem; border: 1px solid rgba(229,57,53,0.15);
}
.badge-pending {
    background: rgba(255,193,7,0.08); color: #FFC107;
    padding: 3px 12px; border-radius: 100px; font-weight: 600;
    font-size: 0.82rem; border: 1px solid rgba(255,193,7,0.12);
}

/* ── Confidence gauge ── */
.gauge-bar {
    height: 4px; background: rgba(255,255,255,0.04);
    border-radius: 2px; overflow: hidden; margin-top: 4px;
}
.gauge-fill { height: 100%; border-radius: 2px; transition: width 0.5s ease; }
.gauge-fill.high { background: #4CAF50; }
.gauge-fill.medium { background: #FFC107; }
.gauge-fill.low { background: #EF5350; }

/* ── Section separator ── */
.section-header {
    display: flex; align-items: center; gap: 0.6rem;
    margin: 2rem 0 1rem 0;
}
.section-header .icon { font-size: 1rem; }
.section-header .title {
    color: #bbb; font-size: 0.85rem; font-weight: 600; letter-spacing: -0.01em;
}
.section-header .line {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(76,175,80,0.12), transparent);
}

/* ── Section tag pill ── */
.section-tag {
    display: inline-block; padding: 4px 12px; border-radius: 100px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: #4CAF50;
    background: rgba(76,175,80,0.06); border: 1px solid rgba(76,175,80,0.1);
    margin-bottom: 8px;
}

/* ── Hero ── */
.hero {
    text-align: center; padding: 2rem 0 1.5rem;
    background: radial-gradient(ellipse at 50% 0%, rgba(76,175,80,0.06) 0%, transparent 60%);
    border-radius: 20px; margin-bottom: 1rem;
}
.hero h1 {
    font-size: 2.4rem !important; margin: 0 !important;
    letter-spacing: -0.04em !important;
}
.hero .tagline {
    color: #4CAF50; font-size: 0.78rem; margin-top: 8px;
    letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;
}
</style>
"""


def apply_theme():
    st.markdown(FOOTBALL_CSS, unsafe_allow_html=True)


def stat_card(title: str, value: str, subtitle: str = "") -> str:
    sub_html = f'<p class="sub">{subtitle}</p>' if subtitle else ""
    return f'<div class="stat-card"><h4>{title}</h4><p class="value">{value}</p>{sub_html}</div>'


def section_header(icon: str, title: str) -> str:
    return (
        f'<div class="section-header">'
        f'<span class="icon">{icon}</span>'
        f'<span class="title">{title}</span>'
        f'<span class="line"></span>'
        f"</div>"
    )


def page_header(icon: str, title: str) -> str:
    return (
        f'<div style="margin-bottom:1rem;">'
        f'<span style="font-size:1.4rem;font-weight:700;'
        f'color:#fff;letter-spacing:-0.02em;">'
        f"{icon} {title}</span></div>"
    )


def section_tag(label: str) -> str:
    return f'<span class="section-tag">{label}</span>'


def confidence_gauge(value: float, label: str = "") -> str:
    pct = max(0, min(100, value * 100))
    if pct >= 65:
        level = "high"
    elif pct >= 45:
        level = "medium"
    else:
        level = "low"
    label_html = f'<span style="color:#888;font-size:0.78rem;">{label}</span>' if label else ""
    return (
        f'<div style="display:inline-block;width:100%;">'
        f"{label_html}"
        f'<div class="gauge-bar">'
        f'<div class="gauge-fill {level}" style="width:{pct:.0f}%;"></div>'
        f"</div></div>"
    )

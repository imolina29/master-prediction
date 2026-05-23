import streamlit as st

FOOTBALL_CSS = """
<style>
/* ── Sidebar: dark-to-green gradient ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B5E20 0%, #0e1117 60%);
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    color: #c8e6c9;
}

/* ── Sidebar navigation items ── */
[data-testid="stSidebarNav"] {
    padding-top: 0.5rem;
}
[data-testid="stSidebarNav"] a {
    border-radius: 8px !important;
    margin: 2px 8px !important;
    padding: 0.45rem 0.8rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(46, 125, 50, 0.2) !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background: rgba(46, 125, 50, 0.25) !important;
    border-left: 3px solid #FFD700 !important;
}
[data-testid="stSidebarNav"] a span {
    color: #c8e6c9 !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] span {
    color: #FFD700 !important;
    font-weight: 600 !important;
}

/* ── User menu popover ── */
[data-testid="stPopover"] > button {
    background: rgba(27, 94, 32, 0.15) !important;
    border: 1px solid rgba(76, 175, 80, 0.25) !important;
    border-radius: 8px !important;
    color: #c8e6c9 !important;
    font-size: 0.85rem !important;
    padding: 0.4rem 0.8rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stPopover"] > button:hover {
    background: rgba(46, 125, 50, 0.25) !important;
    border-color: #4CAF50 !important;
}
[data-testid="stPopoverBody"] {
    background: #1a1a2e !important;
    border: 1px solid rgba(76, 175, 80, 0.2) !important;
    border-radius: 10px !important;
}

/* ── Sidebar section headers ── */
[data-testid="stSidebarNav"] h2 {
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    color: rgba(165, 214, 167, 0.5) !important;
    border-bottom: none !important;
    padding: 0.6rem 0 0.2rem 0.8rem !important;
    margin: 0 !important;
}

/* ── Metric cards: elevated with glow ── */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(27, 94, 32, 0.15), rgba(14, 17, 23, 0.9));
    border: 1px solid rgba(46, 125, 50, 0.25);
    border-left: 4px solid #4CAF50;
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(46, 125, 50, 0.15);
}
[data-testid="stMetricValue"] {
    color: #FFD700 !important;
    font-weight: 700;
}
[data-testid="stMetricDelta"] svg {
    display: inline;
}

/* ── Section headers ── */
h1 {
    color: #4CAF50 !important;
}
h2 {
    color: #66BB6A !important;
    border-bottom: 1px solid rgba(76, 175, 80, 0.2);
    padding-bottom: 6px;
}
h3 {
    color: #81C784 !important;
}

/* ── Dataframes: refined borders ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(76, 175, 80, 0.12);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    border: 1px solid rgba(76, 175, 80, 0.15);
    border-radius: 12px;
    background: rgba(27, 94, 32, 0.05);
}
[data-testid="stExpander"] summary {
    color: #a5d6a7 !important;
}

/* ── Divider ── */
hr {
    border-color: rgba(76, 175, 80, 0.15) !important;
}

/* ── Selectbox / inputs ── */
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stMultiSelect"] label {
    color: #a5d6a7 !important;
    font-weight: 500 !important;
}

/* ── Tab styling ── */
[data-testid="stTabs"] button[aria-selected="true"] {
    border-bottom-color: #4CAF50 !important;
    color: #4CAF50 !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] button {
    color: #81C784 !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: 10px;
}

/* ── Buttons ── */
[data-testid="stButton"] button {
    border-color: rgba(76, 175, 80, 0.3) !important;
    color: #a5d6a7 !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stButton"] button:hover {
    border-color: #4CAF50 !important;
    color: #FFD700 !important;
    background: rgba(46, 125, 50, 0.15) !important;
}

/* ── Custom card class ── */
.stat-card {
    background: linear-gradient(145deg, rgba(27, 94, 32, 0.12), rgba(14, 17, 23, 0.85));
    border: 1px solid rgba(46, 125, 50, 0.2);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}
.stat-card h4 {
    color: #81C784 !important;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 0 0 0.5rem 0;
}
.stat-card .value {
    color: #FFD700;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0;
}
.stat-card .sub {
    color: rgba(200, 230, 201, 0.7);
    font-size: 0.8rem;
    margin: 0.3rem 0 0 0;
}

/* ── Result badges ── */
.badge-win {
    background: rgba(76, 175, 80, 0.2);
    color: #66BB6A;
    padding: 2px 10px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 0.85rem;
}
.badge-loss {
    background: rgba(229, 57, 53, 0.2);
    color: #EF5350;
    padding: 2px 10px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 0.85rem;
}
.badge-pending {
    background: rgba(255, 193, 7, 0.15);
    color: #FFC107;
    padding: 2px 10px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 0.85rem;
}

/* ── Confidence gauge ── */
.gauge-bar {
    height: 6px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 3px;
    overflow: hidden;
    margin-top: 4px;
}
.gauge-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
}
.gauge-fill.high { background: linear-gradient(90deg, #2E7D32, #4CAF50); }
.gauge-fill.medium { background: linear-gradient(90deg, #F57F17, #FFC107); }
.gauge-fill.low { background: linear-gradient(90deg, #C62828, #EF5350); }

/* ── Section separator ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 1.5rem 0 0.8rem 0;
}
.section-header .icon {
    font-size: 1.3rem;
}
.section-header .title {
    color: #66BB6A;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}
.section-header .line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(76, 175, 80, 0.3), transparent);
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


def confidence_gauge(value: float, label: str = "") -> str:
    pct = max(0, min(100, value * 100))
    if pct >= 65:
        level = "high"
    elif pct >= 45:
        level = "medium"
    else:
        level = "low"
    label_html = f'<span style="color:#a5d6a7;font-size:0.8rem;">{label}</span>' if label else ""
    return (
        f'<div style="display:inline-block;width:100%;">'
        f"{label_html}"
        f'<div class="gauge-bar">'
        f'<div class="gauge-fill {level}" style="width:{pct:.0f}%;"></div>'
        f"</div>"
        f"</div>"
    )

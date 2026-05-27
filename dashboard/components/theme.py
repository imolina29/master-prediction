import streamlit as st

FOOTBALL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Base overrides ── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.stMainBlockContainer {
    padding-top: 1.5rem !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #080808;
    border-right: 1px solid rgba(255, 255, 255, 0.04);
}

[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    color: #888;
}

/* ── Sidebar navigation ── */
[data-testid="stSidebarNav"] {
    padding-top: 0.5rem;
}

[data-testid="stSidebarNav"] a {
    border-radius: 10px !important;
    margin: 2px 8px !important;
    padding: 0.5rem 0.9rem !important;
    transition: all 0.2s ease !important;
    border: 1px solid transparent !important;
}

[data-testid="stSidebarNav"] a:hover {
    background: rgba(255, 255, 255, 0.03) !important;
    border-color: rgba(255, 255, 255, 0.06) !important;
}

[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background: rgba(76, 175, 80, 0.06) !important;
    border-color: rgba(76, 175, 80, 0.12) !important;
}

[data-testid="stSidebarNav"] a span {
    color: #777 !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
}

[data-testid="stSidebarNav"] a[aria-selected="true"] span {
    color: #fff !important;
    font-weight: 600 !important;
}

/* ── Sidebar section headers ── */
[data-testid="stSidebarNav"] h2 {
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: #444 !important;
    border-bottom: none !important;
    padding: 0.8rem 0 0.2rem 0.9rem !important;
    margin: 0 !important;
}

/* ── User menu popover ── */
[data-testid="stPopover"] > button {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 10px !important;
    color: #aaa !important;
    font-size: 0.85rem !important;
    padding: 0.4rem 0.8rem !important;
    transition: all 0.2s ease !important;
}

[data-testid="stPopover"] > button:hover {
    background: rgba(255, 255, 255, 0.05) !important;
    border-color: rgba(76, 175, 80, 0.15) !important;
}

[data-testid="stPopoverBody"] {
    background: #0c0c0c !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 12px !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 20px 24px;
    transition: all 0.25s ease;
}

[data-testid="stMetric"]:hover {
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(76, 175, 80, 0.12);
    transform: translateY(-1px);
}

[data-testid="stMetricLabel"] {
    color: #666 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    font-weight: 600 !important;
}

[data-testid="stMetricValue"] {
    color: #fff !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
}

[data-testid="stMetricDelta"] svg {
    display: inline;
}

/* ── Section headers ── */
h1 {
    color: #fff !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
}

h2 {
    color: #fff !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    padding-bottom: 8px;
}

h3 {
    color: #ccc !important;
    font-weight: 600 !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    overflow: hidden;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.01);
}

[data-testid="stExpander"] summary {
    color: #aaa !important;
}

/* ── Divider ── */
hr {
    border-color: rgba(255, 255, 255, 0.05) !important;
}

/* ── Selectbox / inputs ── */
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stMultiSelect"] label {
    color: #888 !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
}

/* ── Tab styling ── */
[data-testid="stTabs"] button[aria-selected="true"] {
    border-bottom-color: #4CAF50 !important;
    color: #fff !important;
    font-weight: 600 !important;
}

[data-testid="stTabs"] button {
    color: #666 !important;
    transition: color 0.2s !important;
}

[data-testid="stTabs"] button:hover {
    color: #aaa !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: 12px;
}

/* ── Buttons ── */
[data-testid="stButton"] button {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: #aaa !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

[data-testid="stButton"] button:hover {
    border-color: rgba(76, 175, 80, 0.2) !important;
    color: #fff !important;
    background: rgba(76, 175, 80, 0.06) !important;
}

/* ── Custom stat card ── */
.stat-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    transition: all 0.25s ease;
}

.stat-card:hover {
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(76, 175, 80, 0.12);
}

.stat-card h4 {
    color: #666 !important;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin: 0 0 0.5rem 0;
}

.stat-card .value {
    color: #fff;
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0;
    line-height: 1.2;
}

.stat-card .sub {
    color: #555;
    font-size: 0.78rem;
    margin: 0.3rem 0 0 0;
}

/* ── Result badges ── */
.badge-win {
    background: rgba(76, 175, 80, 0.1);
    color: #4CAF50;
    padding: 3px 12px;
    border-radius: 100px;
    font-weight: 600;
    font-size: 0.82rem;
    border: 1px solid rgba(76, 175, 80, 0.15);
}

.badge-loss {
    background: rgba(229, 57, 53, 0.1);
    color: #EF5350;
    padding: 3px 12px;
    border-radius: 100px;
    font-weight: 600;
    font-size: 0.82rem;
    border: 1px solid rgba(229, 57, 53, 0.15);
}

.badge-pending {
    background: rgba(255, 193, 7, 0.08);
    color: #FFC107;
    padding: 3px 12px;
    border-radius: 100px;
    font-weight: 600;
    font-size: 0.82rem;
    border: 1px solid rgba(255, 193, 7, 0.12);
}

/* ── Confidence gauge ── */
.gauge-bar {
    height: 4px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
    overflow: hidden;
    margin-top: 4px;
}

.gauge-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s ease;
}

.gauge-fill.high { background: #4CAF50; }
.gauge-fill.medium { background: #FFC107; }
.gauge-fill.low { background: #EF5350; }

/* ── Section separator ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1.5rem 0 0.8rem 0;
}

.section-header .icon {
    font-size: 1.1rem;
}

.section-header .title {
    color: #fff;
    font-size: 0.92rem;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.section-header .line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(255, 255, 255, 0.08), transparent);
}

/* ── Section tag pill ── */
.section-tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #4CAF50;
    background: rgba(76, 175, 80, 0.06);
    border: 1px solid rgba(76, 175, 80, 0.1);
    margin-bottom: 8px;
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
    label_html = (
        f'<span style="color:#888;font-size:0.78rem;">{label}</span>' if label else ""
    )
    return (
        f'<div style="display:inline-block;width:100%;">'
        f"{label_html}"
        f'<div class="gauge-bar">'
        f'<div class="gauge-fill {level}" style="width:{pct:.0f}%;"></div>'
        f"</div>"
        f"</div>"
    )

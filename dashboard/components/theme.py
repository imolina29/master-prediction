import streamlit as st

_FONT_IMPORT = (
    "<style>@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800"
    "&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700"
    "&family=DM+Mono:wght@400;500&display=swap');</style>"
)

FOOTBALL_CSS = """
<style>
/* ══════════════════════════════════════════════════════
   Master Prediction — Design System v2
   ══════════════════════════════════════════════════════ */

/* ── CSS Variables ── */
:root {
    --mp-bg: #07090c;
    --mp-surface: #0c1015;
    --mp-surface-hover: #10151c;
    --mp-border: rgba(255,255,255,0.06);
    --mp-border-hover: rgba(255,255,255,0.10);
    --mp-accent: #16c47f;
    --mp-accent-soft: rgba(22,196,127,0.08);
    --mp-accent-border: rgba(22,196,127,0.18);
    --mp-text-primary: #eef1f5;
    --mp-text-secondary: #8b94a2;
    --mp-text-muted: #6b7382;
    --mp-text-label: #c2cad6;
    --mp-green: #16c47f;
    --mp-green-light: #5fe0a6;
    --mp-yellow: #f5b020;
    --mp-yellow-light: #f5c451;
    --mp-red: #ec3750;
    --mp-red-light: #ff7d92;
    --mp-blue: #7fb0ff;
    --mp-radius-sm: 10px;
    --mp-radius-md: 14px;
    --mp-radius-lg: 18px;
    --mp-font-display: 'Sora', system-ui, -apple-system, sans-serif;
    --mp-font-body: 'DM Sans', system-ui, -apple-system, sans-serif;
    --mp-font-mono: 'DM Mono', 'SF Mono', 'Fira Code', monospace;
    --mp-transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── Hide ALL Streamlit chrome ── */
#MainMenu,
footer,
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.stDeployButton,
#stDecoration,
div[data-testid="stStatusWidget"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    position: fixed !important;
    z-index: -9999 !important;
}

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: var(--mp-font-body) !important;
    background: var(--mp-bg) !important;
}
.stApp { background: var(--mp-bg) !important; }
.stMainBlockContainer {
    padding-top: 1.2rem !important;
    max-width: 1200px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1a1e26; border-radius: 100px; }
::-webkit-scrollbar-thumb:hover { background: #2a2e36; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #090c10 !important;
    border-right: 1px solid var(--mp-border) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    color: var(--mp-text-muted);
}

/* ── Sidebar brand area ── */
.mp-sidebar-brand {
    padding: 1.3rem 1rem 1rem;
    border-bottom: 1px solid var(--mp-border);
    margin-bottom: 0.5rem;
}
.mp-sidebar-brand .logo {
    display: flex;
    align-items: center;
    gap: 10px;
}
.mp-sidebar-brand .logo-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #16c47f, #0fa268);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px;
    box-shadow: 0 4px 16px rgba(22,196,127,0.20);
}
.mp-sidebar-brand .logo-text {
    font-family: var(--mp-font-display);
    font-size: 15px;
    font-weight: 700;
    color: var(--mp-text-primary);
    letter-spacing: -0.02em;
}
.mp-sidebar-brand .logo-sub {
    font-size: 10px;
    color: var(--mp-text-muted);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 500;
    margin-top: 1px;
}

/* ── Sidebar nav ── */
[data-testid="stSidebarNav"] { padding-top: 0.3rem; }

[data-testid="stSidebarNav"] a {
    border-radius: var(--mp-radius-sm) !important;
    margin: 1px 8px !important;
    padding: 0.48rem 0.85rem !important;
    transition: var(--mp-transition) !important;
    border: 1px solid transparent !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: var(--mp-accent-soft) !important;
    border-color: rgba(22,196,127,0.08) !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background: var(--mp-accent-soft) !important;
    border-color: var(--mp-accent-border) !important;
}
[data-testid="stSidebarNav"] a span {
    color: var(--mp-text-muted) !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] span {
    color: var(--mp-text-primary) !important;
    font-weight: 600 !important;
}

/* ── Sidebar section headers ── */
[data-testid="stSidebarNav"] h2 {
    font-size: 0.62rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: var(--mp-text-secondary) !important;
    border-bottom: none !important;
    padding: 0.9rem 0 0.15rem 0.9rem !important;
    margin: 0 !important;
    font-family: var(--mp-font-body) !important;
    font-weight: 600 !important;
}

/* ── User menu popover ── */
[data-testid="stPopover"] > button {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid var(--mp-border) !important;
    border-radius: var(--mp-radius-sm) !important;
    color: var(--mp-text-secondary) !important;
    font-size: 0.82rem !important;
    padding: 0.38rem 0.75rem !important;
    transition: var(--mp-transition) !important;
}
[data-testid="stPopover"] > button:hover {
    background: var(--mp-accent-soft) !important;
    border-color: rgba(22,196,127,0.12) !important;
}
[data-testid="stPopoverBody"] {
    background: var(--mp-surface) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: var(--mp-radius-md) !important;
    box-shadow: 0 16px 48px rgba(0,0,0,0.5) !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: var(--mp-surface);
    border: 1px solid var(--mp-border);
    border-radius: var(--mp-radius-lg);
    padding: 18px 22px;
    transition: var(--mp-transition);
}
[data-testid="stMetric"]:hover {
    border-color: var(--mp-accent-border);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}
[data-testid="stMetricLabel"] {
    color: var(--mp-text-secondary) !important;
    font-size: 0.74rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    color: var(--mp-text-primary) !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    font-family: var(--mp-font-display) !important;
}
[data-testid="stMetricDelta"] svg { display: inline; }

/* ── Headings ── */
h1 {
    color: var(--mp-text-primary) !important;
    font-weight: 800 !important;
    letter-spacing: -0.04em !important;
    font-family: var(--mp-font-display) !important;
}
h2 {
    color: var(--mp-text-primary) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    font-family: var(--mp-font-display) !important;
    border-bottom: 1px solid var(--mp-border) !important;
    padding-bottom: 8px;
}
h3 {
    color: var(--mp-text-label) !important;
    font-weight: 600 !important;
    font-family: var(--mp-font-display) !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--mp-border);
    border-radius: var(--mp-radius-md);
    overflow: hidden;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    border: 1px solid var(--mp-border);
    border-radius: var(--mp-radius-md);
    background: rgba(255,255,255,0.008);
    transition: border-color 0.2s;
}
[data-testid="stExpander"]:hover { border-color: var(--mp-border-hover); }
[data-testid="stExpander"] summary { color: var(--mp-text-label) !important; }

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: var(--mp-radius-sm) !important;
    border: 1px solid var(--mp-border) !important;
    background: rgba(255,255,255,0.012) !important;
    font-size: 0.88rem !important;
}

/* ── Divider ── */
hr { border-color: var(--mp-border) !important; }

/* ── Selectbox / inputs ── */
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label {
    color: var(--mp-text-secondary) !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    background: var(--mp-surface) !important;
    border-color: var(--mp-border) !important;
    border-radius: var(--mp-radius-sm) !important;
    transition: var(--mp-transition) !important;
}
[data-testid="stSelectbox"] > div > div:hover,
[data-testid="stMultiSelect"] > div > div:hover {
    border-color: var(--mp-border-hover) !important;
}
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stMultiSelect"] > div > div:focus-within {
    border-color: rgba(22,196,127,0.30) !important;
    box-shadow: 0 0 0 2px rgba(22,196,127,0.06) !important;
}

/* ── Date input ── */
[data-testid="stDateInput"] input {
    background: var(--mp-surface) !important;
    border-color: var(--mp-border) !important;
    border-radius: var(--mp-radius-sm) !important;
    color: var(--mp-text-primary) !important;
    transition: var(--mp-transition) !important;
}
[data-testid="stDateInput"] input:focus {
    border-color: rgba(22,196,127,0.30) !important;
    box-shadow: 0 0 0 2px rgba(22,196,127,0.06) !important;
}

/* ── Number input ── */
[data-testid="stNumberInput"] input {
    background: var(--mp-surface) !important;
    border-color: var(--mp-border) !important;
    border-radius: var(--mp-radius-sm) !important;
    color: var(--mp-text-primary) !important;
}

/* ── Text input ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: var(--mp-surface) !important;
    border-color: var(--mp-border) !important;
    border-radius: var(--mp-radius-sm) !important;
    color: var(--mp-text-primary) !important;
    transition: var(--mp-transition) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(22,196,127,0.30) !important;
    box-shadow: 0 0 0 2px rgba(22,196,127,0.06) !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] button[aria-selected="true"] {
    border-bottom: 2px solid var(--mp-accent) !important;
    color: var(--mp-text-primary) !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] button {
    color: var(--mp-text-muted) !important;
    transition: color 0.2s !important;
    font-weight: 500 !important;
}
[data-testid="stTabs"] button:hover { color: var(--mp-text-label) !important; }

/* ── Buttons ── */
[data-testid="stButton"] button {
    background: var(--mp-accent-soft) !important;
    border: 1px solid rgba(22,196,127,0.12) !important;
    color: var(--mp-text-label) !important;
    border-radius: var(--mp-radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: var(--mp-transition) !important;
    letter-spacing: 0.01em !important;
}
[data-testid="stButton"] button:hover {
    background: rgba(22,196,127,0.14) !important;
    border-color: rgba(22,196,127,0.25) !important;
    color: var(--mp-text-primary) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(22,196,127,0.10) !important;
}
[data-testid="stButton"] button:active {
    transform: translateY(0) !important;
}

/* ── Primary buttons ── */
button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #16c47f, #0fa268) !important;
    color: #06140e !important;
    border: none !important;
    border-radius: var(--mp-radius-sm) !important;
    font-weight: 700 !important;
    box-shadow: 0 8px 24px rgba(22,196,127,0.25) !important;
}
button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    box-shadow: 0 12px 32px rgba(22,196,127,0.30) !important;
    transform: translateY(-1px) !important;
}

/* ── Plotly transparent bg ── */
.js-plotly-plot .plotly .main-svg { background: transparent !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] { color: var(--mp-accent) !important; }

/* ── Captions ── */
[data-testid="stCaptionContainer"] { color: var(--mp-text-muted) !important; }

/* ── Checkbox ── */
[data-testid="stCheckbox"] label span {
    color: var(--mp-text-muted) !important;
}

/* ── Toast ── */
[data-testid="stToast"] {
    background: var(--mp-surface) !important;
    border: 1px solid var(--mp-border) !important;
    border-radius: var(--mp-radius-md) !important;
    box-shadow: 0 16px 48px rgba(0,0,0,0.4) !important;
}

/* ── Dialog ── */
[data-testid="stDialog"] > div {
    background: var(--mp-surface) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: var(--mp-radius-lg) !important;
    box-shadow: 0 24px 64px rgba(0,0,0,0.5) !important;
}

/* ── Column gap ── */
[data-testid="stHorizontalBlock"] {
    gap: 0.8rem !important;
}

/* ══════════════════════════════════════════════════════
   Custom Components
   ══════════════════════════════════════════════════════ */

/* ── Custom stat card ── */
.mp-stat-card {
    background: var(--mp-surface);
    border: 1px solid var(--mp-border);
    border-radius: var(--mp-radius-lg);
    padding: 1.1rem 1.4rem;
    transition: var(--mp-transition);
}
.mp-stat-card:hover {
    border-color: var(--mp-accent-border);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}
.mp-stat-card.featured {
    border-color: var(--mp-accent-border);
    background: linear-gradient(160deg, #0f2a1e, #0b1411);
}
.mp-stat-card h4 {
    color: var(--mp-text-secondary) !important;
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    font-weight: 600;
    margin: 0 0 0.45rem 0;
    font-family: var(--mp-font-body);
}
.mp-stat-card .value {
    color: var(--mp-text-primary);
    font-size: 1.85rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0;
    line-height: 1.2;
    font-family: var(--mp-font-display);
}
.mp-stat-card .sub {
    color: var(--mp-text-muted);
    font-size: 0.74rem;
    margin: 0.25rem 0 0 0;
}
.mp-stat-card .delta {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 100px;
    font-size: 0.68rem;
    font-weight: 600;
    background: rgba(22,196,127,0.12);
    color: var(--mp-green-light);
    margin-left: 6px;
    vertical-align: middle;
}
.mp-stat-card .progress-bar {
    height: 3px;
    background: rgba(255,255,255,0.04);
    border-radius: 100px;
    margin-top: 10px;
    overflow: hidden;
}
.mp-stat-card .progress-fill {
    height: 100%;
    border-radius: 100px;
    transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── Eyebrow label ── */
.mp-eyebrow {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--mp-accent);
    margin-bottom: 4px;
    font-family: var(--mp-font-body);
}

/* ── Page title ── */
.mp-page-title {
    font-size: 28px;
    font-weight: 800;
    color: var(--mp-text-primary);
    letter-spacing: -0.03em;
    margin: 0 0 3px 0;
    font-family: var(--mp-font-display);
}
.mp-page-subtitle {
    font-size: 13px;
    color: var(--mp-text-secondary);
    margin: 0 0 20px 0;
    line-height: 1.5;
}

/* ── Section header ── */
.mp-section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1.5rem 0 0.8rem 0;
}
.mp-section-header .icon { font-size: 0.95rem; }
.mp-section-header .title {
    color: var(--mp-text-label);
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    font-family: var(--mp-font-display);
}
.mp-section-header .line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(22,196,127,0.12), transparent);
}

/* ── Confidence badges ── */
.mp-badge-alta {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(22,196,127,0.10); color: var(--mp-green-light);
    padding: 3px 11px; border-radius: 100px; font-weight: 600;
    font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.04em;
    border: 1px solid rgba(22,196,127,0.18);
}
.mp-badge-media {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(245,176,32,0.10); color: var(--mp-yellow-light);
    padding: 3px 11px; border-radius: 100px; font-weight: 600;
    font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.04em;
    border: 1px solid rgba(245,176,32,0.18);
}
.mp-badge-baja {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(236,55,80,0.10); color: var(--mp-red-light);
    padding: 3px 11px; border-radius: 100px; font-weight: 600;
    font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.04em;
    border: 1px solid rgba(236,55,80,0.18);
}

/* ── Prediction card ── */
.mp-pred-card {
    background: var(--mp-surface);
    border: 1px solid var(--mp-border);
    border-radius: var(--mp-radius-lg);
    padding: 18px 22px;
    margin-bottom: 10px;
    transition: var(--mp-transition);
}
.mp-pred-card:hover {
    border-color: var(--mp-accent-border);
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}
.mp-pred-card .match-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 3px;
}
.mp-pred-card .teams {
    color: var(--mp-text-primary); font-weight: 700; font-size: 14px;
    letter-spacing: -0.01em; font-family: var(--mp-font-display);
}
.mp-pred-card .meta {
    color: var(--mp-text-muted); font-size: 0.76rem; margin-bottom: 12px;
}
.mp-pred-card .prediction-label {
    color: var(--mp-text-secondary); font-size: 0.80rem; margin-bottom: 8px;
}
.mp-pred-card .prediction-label strong {
    color: var(--mp-text-primary);
}

/* ── Probability bars ── */
.mp-prob-row {
    display: flex; align-items: center; gap: 8px; margin: 4px 0;
}
.mp-prob-row .label {
    color: var(--mp-text-secondary); font-size: 0.78rem; width: 62px; font-weight: 400;
}
.mp-prob-row .label.active {
    color: var(--mp-text-primary); font-weight: 600;
}
.mp-prob-row .bar-bg {
    flex: 1; height: 6px; background: rgba(255,255,255,0.04);
    border-radius: 100px; overflow: hidden;
}
.mp-prob-row .bar-fill {
    height: 100%; border-radius: 100px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.mp-prob-row .bar-fill.active { background: var(--mp-accent); }
.mp-prob-row .bar-fill.inactive { background: rgba(255,255,255,0.07); }
.mp-prob-row .pct {
    color: var(--mp-text-secondary); font-size: 0.78rem; width: 40px; text-align: right;
    font-weight: 400; font-family: var(--mp-font-mono);
}
.mp-prob-row .pct.active {
    color: var(--mp-text-primary); font-weight: 600;
}

/* ── Extras row ── */
.mp-extras {
    color: var(--mp-text-muted); font-size: 0.76rem; margin-top: 10px; padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.04);
}
.mp-extras strong { color: var(--mp-text-label); }

/* ── Confidence distribution bar ── */
.mp-conf-dist {
    display: flex; height: 6px; border-radius: 100px; overflow: hidden;
    background: rgba(255,255,255,0.04); margin-top: 8px;
}
.mp-conf-dist .seg {
    height: 100%; transition: width 0.6s ease;
}

/* ── Filter pills ── */
.mp-filter-pills {
    display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px;
}
.mp-filter-pill {
    padding: 5px 14px; border-radius: 100px;
    font-size: 0.80rem; font-weight: 500;
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    color: var(--mp-text-secondary); cursor: pointer;
    transition: var(--mp-transition);
}
.mp-filter-pill.active {
    background: var(--mp-accent-soft);
    border-color: var(--mp-accent-border);
    color: var(--mp-green-light);
}
.mp-filter-pill .count {
    margin-left: 3px; opacity: 0.6;
    font-family: var(--mp-font-mono);
    font-size: 0.74rem;
}

/* ── Hero (home) ── */
.mp-hero {
    text-align: center;
    padding: 2rem 0 1.8rem;
    background: radial-gradient(120% 90% at 50% 0%, rgba(22,196,127,0.05) 0%, transparent 55%);
    border: 1px solid var(--mp-border);
    border-radius: var(--mp-radius-lg);
    margin-bottom: 1.2rem;
}
.mp-hero h1 {
    font-size: 2.2rem !important;
    margin: 0 !important;
    letter-spacing: -0.04em !important;
    font-family: var(--mp-font-display) !important;
}
.mp-hero .tagline {
    color: var(--mp-accent);
    font-size: 0.72rem;
    margin-top: 6px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 600;
    font-family: var(--mp-font-body);
}

/* ── Result badges ── */
.badge-win {
    background: rgba(22,196,127,0.10); color: var(--mp-green-light);
    padding: 3px 11px; border-radius: 100px; font-weight: 600;
    font-size: 0.80rem; border: 1px solid rgba(22,196,127,0.18);
}
.badge-loss {
    background: rgba(236,55,80,0.10); color: var(--mp-red-light);
    padding: 3px 11px; border-radius: 100px; font-weight: 600;
    font-size: 0.80rem; border: 1px solid rgba(236,55,80,0.18);
}
.badge-pending {
    background: rgba(245,176,32,0.08); color: var(--mp-yellow-light);
    padding: 3px 11px; border-radius: 100px; font-weight: 600;
    font-size: 0.80rem; border: 1px solid rgba(245,176,32,0.15);
}

/* ── Comparator bars ── */
.mp-compare-bar {
    display: flex; align-items: center; gap: 8px; margin: 6px 0;
}
.mp-compare-bar .team-val {
    font-size: 0.82rem; font-weight: 600; width: 38px; text-align: right;
    font-family: var(--mp-font-mono);
}
.mp-compare-bar .bar-track {
    flex: 1; height: 5px; background: rgba(255,255,255,0.04);
    border-radius: 100px; overflow: hidden; position: relative;
}
.mp-compare-bar .bar-a {
    position: absolute; left: 0; height: 100%;
    background: var(--mp-accent); border-radius: 100px;
}
.mp-compare-bar .bar-b {
    position: absolute; right: 0; height: 100%;
    background: var(--mp-blue); border-radius: 100px;
}
.mp-compare-bar .metric-label {
    font-size: 0.76rem; color: var(--mp-text-secondary); width: 70px; text-align: center;
}

/* ── Version tag ── */
.mp-version {
    font-size: 0.62rem;
    color: var(--mp-text-muted);
    opacity: 0.5;
    font-family: var(--mp-font-mono);
    letter-spacing: 0.03em;
    padding: 0.5rem 0.9rem;
}
</style>
"""


def apply_theme():
    st.markdown(_FONT_IMPORT, unsafe_allow_html=True)
    st.markdown(FOOTBALL_CSS, unsafe_allow_html=True)


def sidebar_brand():
    st.markdown(
        '<div class="mp-sidebar-brand">'
        '<div class="logo">'
        '<div class="logo-icon">⚽</div>'
        "<div>"
        '<div class="logo-text">Master Prediction</div>'
        '<div class="logo-sub">Inteligencia Deportiva</div>'
        "</div></div></div>",
        unsafe_allow_html=True,
    )


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
        f'<div style="margin-bottom:0.8rem;">'
        f'<span style="font-size:1.3rem;font-weight:700;'
        f"color:var(--mp-text-primary);letter-spacing:-0.02em;"
        f'font-family:var(--mp-font-display);">'
        f"{icon} {title}</span></div>"
    )


def section_tag(label: str) -> str:
    return (
        f'<span style="display:inline-block;padding:4px 11px;border-radius:100px;'
        f"font-size:0.68rem;font-weight:600;letter-spacing:0.06em;"
        f"text-transform:uppercase;color:var(--mp-accent);"
        f"background:var(--mp-accent-soft);border:1px solid rgba(22,196,127,0.12);"
        f'margin-bottom:6px;">{label}</span>'
    )


def confidence_badge(level: str) -> str:
    dots = {"alta": "#16c47f", "media": "#f5b020", "baja": "#ec3750"}
    dot = dots.get(level, "#6b7382")
    cls = f"mp-badge-{level}" if level in ("alta", "media", "baja") else "mp-badge-baja"
    return (
        f'<span class="{cls}">'
        f'<span style="width:5px;height:5px;border-radius:50%;'
        f'background:{dot};display:inline-block;"></span>'
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
        f'<div class="meta">{date}  ·  {league}</div>'
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
        f'<div style="margin:12px 0;">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:5px;">'
        f'<span style="font-size:0.74rem;color:var(--mp-green-light);font-weight:600;">'
        f"Alta {alta}</span>"
        f'<span style="font-size:0.74rem;color:var(--mp-yellow-light);font-weight:600;">'
        f"Media {media}</span>"
        f'<span style="font-size:0.74rem;color:var(--mp-red-light);font-weight:600;">'
        f"Baja {baja}</span>"
        f"</div>"
        f'<div class="mp-conf-dist">'
        f'<div class="seg" style="width:{pa:.0f}%;background:var(--mp-green);"></div>'
        f'<div class="seg" style="width:{pm:.0f}%;background:var(--mp-yellow);"></div>'
        f'<div class="seg" style="width:{pb:.0f}%;background:var(--mp-red);"></div>'
        f"</div>"
        f"</div>"
    )


def confidence_gauge(value: float, label: str = "") -> str:
    pct = max(0, min(100, value * 100))
    if pct >= 65:
        color = "var(--mp-green)"
    elif pct >= 45:
        color = "var(--mp-yellow)"
    else:
        color = "var(--mp-red)"
    label_html = (
        f'<span style="color:var(--mp-text-secondary);font-size:0.76rem;">{label}</span>'
        if label
        else ""
    )
    return (
        f'<div style="display:inline-block;width:100%;">'
        f"{label_html}"
        f'<div style="height:3px;background:rgba(255,255,255,0.04);'
        f'border-radius:100px;overflow:hidden;margin-top:4px;">'
        f'<div style="height:100%;border-radius:100px;'
        f"width:{pct:.0f}%;background:{color};"
        f'transition:width 0.6s ease;"></div>'
        f"</div></div>"
    )

"""Design system V3 — broadcast-inspired sports analytics."""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --ground: #0f1114;
  --surface: #191c21;
  --edge: #282c34;
  --flame: #e8590c;
  --flame-dim: rgba(232, 89, 12, 0.12);
  --hit: #2da44e;
  --hit-dim: rgba(45, 164, 78, 0.12);
  --miss: #cf222e;
  --miss-dim: rgba(207, 34, 46, 0.12);
  --info: #58a6ff;
  --info-dim: rgba(88, 166, 255, 0.12);
  --draw-color: #d29922;
  --draw-dim: rgba(210, 153, 34, 0.12);
  --text-1: #e6edf3;
  --text-2: #7d8590;
  --text-3: #484f58;
  --mono: 'JetBrains Mono', ui-monospace, 'SF Mono', monospace;
  --sans: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  --radius: 3px;
}

* { box-sizing: border-box; }
body {
  font-family: var(--sans) !important;
  background: var(--ground) !important;
  color: var(--text-1);
  -webkit-font-smoothing: antialiased;
}

/* NiceGUI overrides */
.nicegui-content { background: var(--ground) !important; }
.q-page { background: var(--ground) !important; }
.q-page > div, .q-page > div > div { width: 100%; }
nicegui-html { width: 100%; display: block; }
.q-drawer { background: var(--surface) !important; border-right: 1px solid var(--edge) !important; }
.q-drawer--left { width: 220px !important; }
.q-header { background: transparent !important; box-shadow: none !important; }
.q-layout__section--marginal { background: transparent !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.15); border-radius: 100px; }

/* ── SIDEBAR ── */
.mp-sidebar {
  display: flex; flex-direction: column;
  padding: 16px 12px; height: 100%;
}
.s-brand {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 24px; padding: 0 4px;
}
.s-logo {
  width: 32px; height: 32px; min-width: 32px;
  background: var(--flame);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 900; font-size: 14px; color: #fff;
  letter-spacing: -0.04em;
  font-family: var(--sans);
}
.s-brand-text {
  font-size: 14px; font-weight: 800; color: var(--text-1);
  letter-spacing: -0.03em; line-height: 1.1;
}
.s-nav { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.s-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  color: var(--text-3);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  position: relative;
  text-decoration: none !important;
  font-size: 13px; font-weight: 500;
}
.s-item:hover { background: var(--edge); color: var(--text-2); }
.s-item.active {
  color: var(--flame);
  background: var(--flame-dim);
}
.s-item.active::before {
  content: '';
  position: absolute; left: -12px;
  width: 3px; height: 20px;
  background: var(--flame);
  border-radius: 0 2px 2px 0;
}
.s-icon { display: flex; align-items: center; justify-content: center; width: 18px; height: 18px; }
.s-icon svg { width: 18px; height: 18px; }
.s-label { white-space: nowrap; }
.s-sep { height: 1px; background: var(--edge); margin: 8px 4px; }
.s-bottom { margin-top: auto; padding: 0 4px; }
.s-user {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 4px;
}
.s-avatar {
  width: 28px; height: 28px; min-width: 28px;
  background: var(--edge);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: var(--text-2);
  font-family: var(--sans);
}
.s-user-name {
  font-size: 12px; color: var(--text-2); font-weight: 500;
}
.s-logout {
  width: 28px; height: 28px; min-width: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px; border: none;
  background: transparent; color: var(--text-3);
  cursor: pointer; transition: background 0.15s, color 0.15s;
  margin-left: auto; padding: 0;
}
.s-logout:hover { background: var(--edge); color: var(--miss); }

/* ── TOPBAR ── */
.topbar {
  display: flex; justify-content: space-between;
  align-items: baseline; margin-bottom: 24px;
  width: 100%;
}
.topbar h1 {
  font-size: 20px; font-weight: 800;
  letter-spacing: -0.03em; color: var(--text-1);
  font-family: var(--sans); margin: 0;
}
.topbar h1 span { color: var(--flame); }
.topbar .meta {
  font-size: 12px; color: var(--text-3);
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}

/* ── FEATURED MATCH ── */
.featured {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  overflow: hidden; margin-bottom: 24px;
}
.f-stripe {
  height: 3px;
  background: linear-gradient(90deg, var(--flame) 0%, var(--flame) 55%, var(--edge) 55%);
}
.f-label {
  display: flex; justify-content: space-between;
  align-items: center; padding: 12px 20px 0;
}
.f-tag {
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.10em;
  color: var(--flame);
}
.f-league {
  font-size: 11px; color: var(--text-3);
  font-family: var(--mono);
}
.f-body {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 16px 20px 12px; gap: 20px;
}
.f-team { display: flex; flex-direction: column; gap: 4px; }
.f-team.away { text-align: right; }
.f-team-name {
  font-size: 22px; font-weight: 800;
  letter-spacing: -0.03em; line-height: 1.1;
}
.f-team-sub { font-size: 11px; color: var(--text-3); }
.f-vs {
  display: flex; flex-direction: column;
  align-items: center; gap: 2px;
}
.f-vs-label {
  font-size: 10px; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600;
}
.f-vs-date {
  font-size: 12px; color: var(--text-2);
  font-family: var(--mono); font-variant-numeric: tabular-nums;
}

/* ── FORCE BAR ── */
.force-bar { padding: 0 20px 16px; }
.force-track {
  display: flex; height: 28px;
  border-radius: 2px; overflow: hidden;
  background: var(--edge);
}
.force-seg {
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
  font-family: var(--mono);
  color: rgba(255,255,255,0.9);
  min-width: 36px;
}
.force-seg.home { background: var(--info); }
.force-seg.draw { background: var(--draw-color); }
.force-seg.away { background: var(--miss); }
.force-labels {
  display: flex; justify-content: space-between;
  margin-top: 6px; font-size: 10px; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600;
}
.force-labels .pick { color: var(--flame); font-weight: 700; }
.f-extras {
  display: flex; gap: 24px;
  padding: 0 20px 14px;
  font-size: 11px; color: var(--text-3);
}
.f-extras strong { color: var(--text-2); font-weight: 600; }

/* ── GRID ── */
.mp-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px; align-items: start;
}
@media (max-width: 860px) { .mp-grid { grid-template-columns: 1fr; } }

/* ── MATCH LIST ── */
.match-list {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
}
.ml-head {
  display: flex; justify-content: space-between;
  align-items: center; padding: 12px 16px;
  border-bottom: 1px solid var(--edge);
}
.ml-head h2 {
  font-size: 13px; font-weight: 700;
  letter-spacing: -0.01em; margin: 0;
}
.ml-head .count {
  font-size: 11px; color: var(--text-3);
  font-family: var(--mono);
}
.ml-row {
  display: grid;
  grid-template-columns: 3px 1fr 160px;
  border-bottom: 1px solid var(--edge);
  transition: background 0.1s;
}
.ml-row:last-child { border-bottom: none; }
.ml-row:hover { background: rgba(255,255,255,0.015); }
.ml-conf { border-radius: 0; }
.ml-conf.alta { background: var(--hit); }
.ml-conf.media { background: var(--draw-color); }
.ml-conf.baja { background: var(--miss); }
.ml-info {
  padding: 10px 14px;
  display: flex; flex-direction: column; gap: 2px;
}
.ml-teams {
  font-size: 13px; font-weight: 600;
  letter-spacing: -0.01em;
}
.ml-meta {
  font-size: 10px; color: var(--text-3);
  display: flex; gap: 8px; align-items: center;
}
.ml-meta .league-dot {
  width: 5px; height: 5px;
  border-radius: 50%; display: inline-block;
}
.ml-force {
  padding: 10px 14px;
  display: flex; flex-direction: column;
  justify-content: center; gap: 3px;
}
.ml-force-track {
  display: flex; height: 14px;
  border-radius: 2px; overflow: hidden;
  background: var(--edge);
}
.ml-force-seg {
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; font-weight: 700;
  font-family: var(--mono);
  color: rgba(255,255,255,0.85);
  min-width: 24px;
}
.ml-force-seg.home { background: var(--info); }
.ml-force-seg.draw { background: var(--draw-color); }
.ml-force-seg.away { background: var(--miss); }
.ml-pred {
  font-size: 10px; color: var(--text-3); text-align: right;
}
.ml-pred strong { color: var(--text-2); font-weight: 600; }

/* ── RIGHT COL PANELS ── */
.donut-panel, .spark-panel, .leagues-panel {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
}
.donut-panel { padding: 16px; }
.donut-panel h3, .spark-panel h3 {
  font-size: 12px; font-weight: 700;
  letter-spacing: -0.01em; margin: 0 0 12px;
}
.donut-wrap {
  display: flex; align-items: center; gap: 20px;
}
.donut-stats { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.donut-stat {
  display: flex; justify-content: space-between;
  align-items: center; font-size: 12px;
}
.ds-label {
  display: flex; align-items: center; gap: 6px; color: var(--text-2);
}
.ds-dot { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }
.ds-val {
  font-weight: 700; font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}

.spark-panel { padding: 16px; }
.sp-sub { font-size: 11px; color: var(--text-3); margin-bottom: 12px; }
.spark-big {
  font-size: 32px; font-weight: 900;
  letter-spacing: -0.04em; line-height: 1; margin-bottom: 2px;
}
.spark-big .unit { font-size: 18px; color: var(--text-2); font-weight: 700; }

/* ── TRACK RECORD ── */
.track-panel {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  margin-top: 20px;
}
.tp-head {
  display: flex; justify-content: space-between;
  align-items: center; padding: 12px 16px;
  border-bottom: 1px solid var(--edge);
}
.tp-head h2 { font-size: 13px; font-weight: 700; margin: 0; }
.streak { display: flex; gap: 3px; }
.streak .dot {
  width: 14px; height: 14px;
  border-radius: 2px;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 800; color: #fff;
}
.streak .dot.w { background: var(--hit); }
.streak .dot.l { background: var(--miss); }
.tp-row {
  display: grid;
  grid-template-columns: 70px 1fr 50px 60px 28px;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid var(--edge);
  font-size: 12px;
}
.tp-row:last-child { border-bottom: none; }
.tp-row:hover { background: rgba(255,255,255,0.015); }
.tp-date {
  color: var(--text-3); font-family: var(--mono);
  font-size: 11px; font-variant-numeric: tabular-nums;
}
.tp-match { font-weight: 500; }
.tp-score {
  font-family: var(--mono); font-weight: 700;
  text-align: center; font-variant-numeric: tabular-nums;
}
.tp-pred { color: var(--text-3); font-size: 11px; }
.tp-icon { text-align: center; }
.tp-check {
  width: 18px; height: 18px; border-radius: 2px;
  display: inline-flex; align-items: center; justify-content: center;
}
.tp-check.ok { background: var(--hit-dim); color: var(--hit); }
.tp-check.no { background: var(--miss-dim); color: var(--miss); }
.tp-check svg { width: 12px; height: 12px; }

/* ── LEAGUES ── */
.lp-row {
  display: grid;
  grid-template-columns: 1fr 60px 80px;
  align-items: center;
  padding: 9px 16px;
  border-bottom: 1px solid var(--edge);
  font-size: 12px;
}
.lp-row:last-child { border-bottom: none; }
.lp-name { font-weight: 500; }
.lp-record {
  color: var(--text-3); font-family: var(--mono);
  text-align: center; font-variant-numeric: tabular-nums;
}
.lp-pct {
  font-weight: 700; font-family: var(--mono);
  text-align: right; font-variant-numeric: tabular-nums;
}

/* ── LOGIN ── */
.login-wrap {
  min-height: 100vh; width: 100%;
  display: flex; align-items: center; justify-content: center;
  background: var(--ground);
}
.login-box { width: 100%; max-width: 400px; padding: 0 20px; }
.login-header { text-align: center; margin-bottom: 24px; }
.login-icon {
  width: 48px; height: 48px;
  background: var(--flame);
  border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 900; color: #fff;
  margin-bottom: 16px;
  font-family: var(--sans);
}
.login-header h1 {
  font-size: 22px; font-weight: 800;
  letter-spacing: -0.02em; margin: 0 0 4px;
}
.login-header h1 span { color: var(--flame); }
.login-header p { font-size: 13px; color: var(--text-3); margin: 0; }
.login-form {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  padding: 24px;
}
.login-form .q-field__label { color: var(--text-3) !important; }
.login-form .q-field__control {
  background: var(--ground) !important;
  border-radius: var(--radius) !important;
}
.login-form .q-btn {
  background: var(--flame) !important;
  border-radius: var(--radius) !important;
  font-weight: 700 !important;
  text-transform: none !important;
  font-size: 13px !important;
}
.login-stats {
  display: flex; justify-content: center; gap: 32px; margin-top: 24px;
}
.login-stat { text-align: center; }
.login-stat .val {
  font-size: 20px; font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.login-stat .lbl {
  font-size: 10px; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px;
}

/* ── KPI ROW ── */
.kpi-row {
  display: flex; gap: 16px; margin: 12px 0 20px;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  padding: 14px 20px; flex: 1; min-width: 0;
}
.kpi-val {
  font-size: 24px; font-weight: 900;
  letter-spacing: -0.04em; line-height: 1;
  font-variant-numeric: tabular-nums;
}
.kpi-lbl {
  font-size: 10px; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-top: 4px;
}

/* ── PRED GRID ── */
.pred-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px; margin-top: 12px;
}
.pred-card {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  padding: 14px 16px;
}
.pc-top {
  display: flex; justify-content: space-between;
  font-size: 10px; color: var(--text-3);
  margin-bottom: 6px;
}
.pc-league { text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
.pc-date { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.pc-teams {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 15px; font-weight: 700; letter-spacing: -0.02em;
}
.pc-vs { font-size: 10px; color: var(--text-3); font-weight: 400; }
.pc-bottom {
  display: flex; gap: 12px; font-size: 11px; color: var(--text-3); margin-top: 6px;
}
.pc-pred strong { color: var(--text-2); }
.pc-extras { margin-left: auto; font-family: var(--mono); }

/* ── WC GROUPS ── */
.wc-groups {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
@media (max-width: 860px) { .wc-groups { grid-template-columns: repeat(2, 1fr); } }
.wc-group {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  padding: 10px 12px;
}
.wc-group-title {
  font-size: 11px; font-weight: 700;
  color: var(--flame); margin-bottom: 6px;
  text-transform: uppercase; letter-spacing: 0.06em;
}
.wc-row {
  display: flex; justify-content: space-between;
  align-items: center;
  padding: 4px 6px; font-size: 12px;
  border-radius: 2px; margin-bottom: 1px;
}
.wc-row.q1 { background: var(--hit-dim); }
.wc-row.q3 { background: var(--draw-dim); }
.wc-team { font-weight: 500; }
.wc-pts {
  font-family: var(--mono); font-variant-numeric: tabular-nums;
  display: flex; gap: 6px; align-items: baseline;
}
.wc-pts strong { font-size: 13px; }
.wc-pts small { font-size: 10px; color: var(--text-3); }

/* ── BRACKET ── */
.bracket-wrap { overflow-x: auto; padding: 8px 0; }
.bk-labels {
  display: flex; align-items: center; justify-content: center;
  gap: 2px; margin-bottom: 6px;
}
.bk-labels span {
  min-width: 110px; text-align: center;
  font-size: 10px; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.08em;
}
.bk-bracket {
  display: flex; align-items: stretch; min-height: 520px;
}
.bk-round {
  display: flex; flex-direction: column;
  min-width: 110px; margin: 0 2px;
}
.bk-pair {
  flex: 1; display: flex; flex-direction: column;
  justify-content: center; gap: 4px;
}
.bk-slot {
  flex: 1; display: flex; align-items: center;
}
.bk-game {
  border: 1px solid var(--edge); border-radius: var(--radius);
  background: var(--surface); width: 100%;
}
.bk-tr {
  display: flex; justify-content: space-between;
  padding: 3px 6px; font-size: 11px;
}
.bk-tr + .bk-tr { border-top: 1px solid var(--edge); }
.bk-sc { font-weight: 700; color: var(--flame); }
.bk-conns { display: flex; flex-direction: column; width: 16px; }
.bk-cl {
  flex: 1; position: relative;
}
.bk-cl::before {
  content: ''; position: absolute; left: 0; width: 8px;
  top: 25%; height: 50%;
  border: 1.5px solid var(--edge); border-left: none;
  border-radius: 0 3px 3px 0;
}
.bk-cl::after {
  content: ''; position: absolute; left: 8px; right: 0;
  top: 50%; border-top: 1.5px solid var(--edge);
}
.bk-cr {
  flex: 1; position: relative;
}
.bk-cr::before {
  content: ''; position: absolute; right: 0; width: 8px;
  top: 25%; height: 50%;
  border: 1.5px solid var(--edge); border-right: none;
  border-radius: 3px 0 0 3px;
}
.bk-cr::after {
  content: ''; position: absolute; right: 8px; left: 0;
  top: 50%; border-top: 1.5px solid var(--edge);
}
.bk-hl { flex: 1; position: relative; }
.bk-hl::after {
  content: ''; position: absolute; left: 0; right: 0;
  top: 50%; border-top: 1.5px solid var(--edge);
}
.bk-final {
  display: flex; flex-direction: column;
  min-width: 120px; justify-content: center; align-items: center;
}
.bk-fl {
  font-size: 12px; font-weight: 700;
  color: var(--flame); text-align: center; margin-bottom: 4px;
}
.bk-final .bk-game { width: 110px; }

/* ── STANDINGS ── */
.standings-panel {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  overflow-x: auto;
}
.st-table { min-width: 600px; }
.st-header, .st-row {
  display: grid;
  grid-template-columns: 32px 1fr repeat(8, 36px) 90px;
  align-items: center;
  padding: 6px 12px;
  border-bottom: 1px solid var(--edge);
  font-size: 12px;
}
.st-header {
  color: var(--text-3); font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.04em; font-size: 10px;
}
.st-row:last-child { border-bottom: none; }
.st-row:hover { background: rgba(255,255,255,0.015); }
.st-pos { text-align: center; color: var(--text-3); font-weight: 600; }
.st-team { font-weight: 600; letter-spacing: -0.01em; }
.st-num {
  text-align: center; font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}
.st-pts { font-weight: 700; color: var(--text-1); }
.st-form { padding-left: 4px; }
.st-row.ucl { border-left: 3px solid var(--info); }
.st-row.rel { border-left: 3px solid var(--miss); }
.streak .dot.d { background: var(--draw-color); }

/* ── COMPARATOR ── */
.compare-section { margin-top: 16px; }
.cmp-row {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 2px;
}
.cmp-val {
  font-family: var(--mono); font-size: 12px; font-weight: 700;
  min-width: 48px; text-align: center;
  font-variant-numeric: tabular-nums;
}
.cmp-track {
  flex: 1; height: 16px; display: flex;
  background: var(--edge); border-radius: 2px; overflow: hidden;
  justify-content: center;
}
.cmp-bar-a {
  background: var(--hit); height: 100%;
  border-radius: 2px 0 0 2px;
}
.cmp-bar-b {
  background: var(--info); height: 100%;
  border-radius: 0 2px 2px 0;
}
.cmp-label {
  text-align: center; font-size: 10px; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-bottom: 10px;
}

/* ── FOOTER ── */
.mp-footer {
  width: 100%;
  border-top: 1px solid var(--edge);
  margin-top: 48px;
  padding: 24px 0 16px;
  display: flex; flex-direction: column;
  align-items: center; gap: 12px;
  text-align: center;
  margin-left: auto; margin-right: auto;
}
.mp-footer-brand {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 700; color: var(--text-2);
  letter-spacing: -0.02em;
}
.mp-footer-brand .ft-logo {
  width: 22px; height: 22px;
  background: var(--flame);
  border-radius: 5px;
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; font-weight: 900; color: #fff;
  font-family: var(--sans);
}
.mp-footer-brand span { color: var(--flame); }
.mp-footer-legal {
  text-align: center;
  font-size: 10px; color: var(--text-3);
  line-height: 1.8;
  max-width: 520px;
}
.mp-footer-legal a {
  color: var(--text-3); text-decoration: underline;
  text-underline-offset: 2px;
}
.mp-footer-legal a:hover { color: var(--text-2); }
.mp-footer-badges {
  display: flex; gap: 16px; align-items: center;
  margin-top: 4px;
}
.mp-footer-badge {
  display: flex; align-items: center; gap: 5px;
  font-size: 10px; color: var(--text-3);
  padding: 4px 10px;
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}
.mp-footer-badge svg { width: 12px; height: 12px; }

/* ── PLACEHOLDER ── */
.placeholder-box {
  background: var(--surface);
  border: 1px solid var(--edge);
  border-radius: var(--radius);
  text-align: center; padding: 48px 24px;
  margin-top: 24px;
}
.placeholder-box .ph-icon { font-size: 48px; margin-bottom: 16px; }
.placeholder-box .ph-title {
  color: var(--text-2); font-size: 15px; font-weight: 500;
}
.placeholder-box .ph-sub {
  color: var(--text-3); font-size: 13px; margin-top: 8px;
}
.page-eyebrow {
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.10em;
  color: var(--flame); margin-bottom: 4px;
}
.page-title {
  font-size: 20px; font-weight: 800;
  letter-spacing: -0.03em;
}

/* ── HERO BANNER ── */
.mp-hero {
  position: relative;
  width: 100%;
  min-height: 200px;
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 24px;
  background-color: var(--surface);
}
.mp-hero-img, .mp-hero-img img {
  position: absolute; inset: 0;
  width: 100% !important; height: 100% !important;
  object-fit: cover;
  margin: 0 !important; padding: 0 !important;
}
.mp-hero-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(15,17,20,0.62), rgba(15,17,20,0.35));
  display: flex; flex-direction: column;
  justify-content: center; padding: 32px 36px;
}
.mp-hero h1 {
  font-size: 28px; font-weight: 800;
  letter-spacing: -0.03em; margin: 0;
  font-family: var(--sans);
}
.mp-hero h1 span { color: var(--flame); }
.mp-hero .hero-tagline {
  font-size: 13px; color: var(--text-2);
  margin-top: 4px; font-family: var(--sans);
}
.mp-hero .hero-date {
  font-size: 11px; color: var(--text-3);
  font-family: var(--mono); margin-top: 2px;
  font-variant-numeric: tabular-nums;
}
.mp-hero-kpis {
  display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap;
}
.mp-hero-kpi {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 8px; padding: 10px 18px;
  text-align: center; min-width: 90px;
}
.mp-hero-kpi .kpi-v {
  font-size: 20px; font-weight: 800;
  color: var(--text-1); font-variant-numeric: tabular-nums;
}
.mp-hero-kpi .kpi-l {
  font-size: 10px; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.05em;
  margin-top: 2px;
}

/* ── MINI STRIP ── */
.mp-strip {
  position: relative;
  width: 100%;
  height: 56px;
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 20px;
  background-color: var(--surface);
}
.mp-strip-img, .mp-strip-img img {
  position: absolute; inset: 0;
  width: 100% !important; height: 100% !important;
  object-fit: cover;
  margin: 0 !important; padding: 0 !important;
}
.mp-strip-overlay {
  position: absolute; inset: 0;
  background: rgba(15,17,20,0.65);
  display: flex; align-items: center;
  padding: 0 20px; gap: 10px;
}
.mp-strip-icon {
  width: 20px; height: 20px;
  color: var(--flame); flex-shrink: 0;
}
.mp-strip-eyebrow {
  font-size: 10px; color: var(--flame);
  text-transform: uppercase; letter-spacing: 0.06em;
  font-weight: 600;
}
.mp-strip-title {
  font-size: 16px; font-weight: 700;
  letter-spacing: -0.02em;
}
.mp-strip-date {
  margin-left: auto;
  font-size: 11px; color: var(--text-3);
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}
"""

SIDEBAR_ICONS = {
    "home": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/></svg>',
    "grid": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    "pulse": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "gear": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
    "trophy": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 9H4.5a2.5 2.5 0 010-5H6"/><path d="M18 9h1.5a2.5 2.5 0 000-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 19.24 7 20v2h10v-2c0-.76-.85-1.25-2.03-1.79C14.47 17.98 14 17.55 14 17v-2.34"/><path d="M18 2H6v7a6 6 0 1012 0V2z"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "scale": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v18"/><path d="M16 7l-8 0"/><path d="M18 11l-2-4"/><path d="M6 11l2-4"/><circle cx="18" cy="13" r="2"/><circle cx="6" cy="13" r="2"/></svg>',
    "chat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
    "target": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
}


def render_topbar():
    """Render the topbar using native NiceGUI components."""
    from datetime import datetime, timedelta, timezone

    from nicegui import ui

    col_tz = timezone(timedelta(hours=-5))
    now_str = datetime.now(col_tz).strftime("%b %d %Y · %H:%M COT").lower()
    with ui.row().classes("w-full justify-between items-baseline mb-6"):
        ui.html(
            '<h1 style="font-size:20px;font-weight:800;letter-spacing:-0.03em;margin:0;font-family:var(--sans)">Master <span style="color:var(--flame)">Prediction</span></h1>'
        )
        ui.label(now_str).style(
            "font-size:12px;color:var(--text-3);font-family:var(--mono);"
            "font-variant-numeric:tabular-nums"
        )


def render_hero_banner(stats: dict):
    """Hero banner for Home with stadium background and KPIs."""
    from datetime import datetime, timedelta, timezone

    from nicegui import ui

    col_tz = timezone(timedelta(hours=-5))
    now_str = datetime.now(col_tz).strftime("%b %d %Y · %H:%M COT").lower()
    matches = stats.get("matches", 0)
    hit_rate = stats.get("hit_rate", 0)
    leagues = stats.get("leagues", 0)
    with ui.element("div").classes("mp-hero"):
        ui.image("/static/hero-stadium.jpg").classes("mp-hero-img")
        with ui.element("div").classes("mp-hero-overlay"):
            ui.html("<h1>Master <span>Prediction</span></h1>")
            ui.label("Inteligencia deportiva potenciada con IA").style(
                "font-size:13px;color:var(--text-2);margin-top:4px"
            )
            ui.label(now_str).style(
                "font-size:11px;color:var(--text-3);font-family:var(--mono);"
                "font-variant-numeric:tabular-nums;margin-top:2px"
            )
            with ui.row().classes("mp-hero-kpis"):
                for val, lbl in [
                    (f"{matches:,}", "Partidos"),
                    (f"{round(hit_rate * 100)}%", "Acierto"),
                    (str(leagues), "Ligas"),
                ]:
                    with ui.element("div").classes("mp-hero-kpi"):
                        ui.label(val).style(
                            "font-size:20px;font-weight:800;font-variant-numeric:tabular-nums"
                        )
                        ui.label(lbl).style(
                            "font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.05em;margin-top:2px"
                        )


def render_mini_strip(title: str, eyebrow: str, icon_key: str):
    """Compact image strip for non-home pages."""
    from datetime import datetime, timedelta, timezone

    from nicegui import ui

    col_tz = timezone(timedelta(hours=-5))
    now_str = datetime.now(col_tz).strftime("%b %d %Y · %H:%M COT").lower()
    icon_svg = SIDEBAR_ICONS.get(icon_key, "")
    with ui.element("div").classes("mp-strip"):
        ui.image("/static/strip-pitch.jpg").classes("mp-strip-img")
        with ui.row().classes("mp-strip-overlay"):
            ui.html(f'<div class="mp-strip-icon">{icon_svg}</div>')
            with ui.element("div"):
                ui.label(eyebrow).style(
                    "font-size:10px;color:var(--flame);text-transform:uppercase;"
                    "letter-spacing:0.06em;font-weight:600"
                )
                ui.label(title).style("font-size:16px;font-weight:700;letter-spacing:-0.02em")
            ui.label(now_str).style(
                "margin-left:auto;font-size:11px;color:var(--text-3);"
                "font-family:var(--mono);font-variant-numeric:tabular-nums"
            )


_AI_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2a4 4 0 014 4v1a4 4 0 01-8 0V6a4 4 0 014-4z"/><path d="M6 10v1a6 6 0 0012 0v-1"/><path d="M12 17v5"/><path d="M8 22h8"/></svg>'
_SHIELD_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'


def render_footer():
    """Render the legal footer at the bottom of the page."""
    from nicegui import ui

    year = __import__("datetime").datetime.now().year
    with (
        ui.column()
        .classes("w-full items-center")
        .style("border-top:1px solid var(--edge);margin-top:48px;padding:24px 0 16px;gap:12px")
    ):
        with ui.row().classes("items-center gap-2"):
            ui.html('<div class="ft-logo">MP</div>')
            ui.html(
                '<span style="font-size:13px;font-weight:700;color:var(--text-2)">Master <span style="color:var(--flame)">Prediction</span></span>'
            )
        with ui.row().classes("gap-4 items-center").style("margin-top:4px"):
            ui.html(f'<div class="mp-footer-badge">{_AI_ICON} AI-Powered</div>')
            ui.html(f'<div class="mp-footer-badge">{_SHIELD_ICON} Datos protegidos</div>')
        ui.html(
            f'<div style="text-align:center;font-size:10px;color:var(--text-3);line-height:1.8;max-width:520px">'
            f"&copy; {year} Master Prediction. Todos los derechos reservados.<br>"
            f"Plataforma de inteligencia deportiva potenciada por inteligencia artificial.<br>"
            f"Las predicciones son de caracter informativo y no constituyen asesoria financiera ni incentivo a apuestas.<br>"
            f"El uso de esta plataforma implica la aceptacion de los "
            f'<a href="#" style="color:var(--text-3);text-decoration:underline">Terminos de Servicio</a> y la '
            f'<a href="#" style="color:var(--text-3);text-decoration:underline">Politica de Privacidad</a>.'
            f"</div>"
        )
        ui.label(
            "Master Prediction v2.0 · Modelo Poisson + XGBoost · Datos actualizados en tiempo real"
        ).style("font-size:10px;color:var(--text-3);margin-top:2px")


CHECK_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>'
CROSS_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'

DONUT_JS = """
(function() {
  const c = document.getElementById('donut-chart');
  if (!c) return;
  const ctx = c.getContext('2d');
  const cx = 50, cy = 50, r = 38, lw = 10;
  const hitPct = parseFloat(c.dataset.hit || '0.6');
  const data = [
    { pct: hitPct, color: '#2da44e' },
    { pct: 1 - hitPct, color: '#cf222e' },
  ];
  let start = -Math.PI / 2;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = '#282c34'; ctx.lineWidth = lw; ctx.stroke();
  data.forEach(d => {
    const sweep = d.pct * Math.PI * 2;
    ctx.beginPath(); ctx.arc(cx, cy, r, start, start + sweep);
    ctx.strokeStyle = d.color; ctx.lineWidth = lw; ctx.stroke();
    start += sweep;
  });
  ctx.fillStyle = '#e6edf3';
  ctx.font = '900 22px Inter, -apple-system, sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(Math.round(hitPct * 100) + '%', cx, cy - 2);
  ctx.fillStyle = '#484f58';
  ctx.font = '600 8px Inter, -apple-system, sans-serif';
  ctx.fillText('ACIERTO', cx, cy + 12);
})();
"""

SPARK_JS = """
(function() {
  const c = document.getElementById('spark-chart');
  if (!c) return;
  const ctx = c.getContext('2d');
  const w = c.width, h = c.height;
  const raw = c.dataset.points || '';
  const points = raw ? raw.split(',').map(Number) : [50,55,58,60,62,65,63,68,72];
  if (points.length < 2) return;
  const min = Math.min(...points) - 5, max = Math.max(...points) + 5;
  const px = points.map((v, i) => (i / (points.length - 1)) * (w - 8) + 4);
  const py = points.map(v => h - 6 - ((v - min) / (max - min)) * (h - 12));
  ctx.beginPath();
  ctx.moveTo(px[0], h);
  px.forEach((x, i) => ctx.lineTo(x, py[i]));
  ctx.lineTo(px[px.length - 1], h);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, 'rgba(232, 89, 12, 0.20)');
  grad.addColorStop(1, 'rgba(232, 89, 12, 0.00)');
  ctx.fillStyle = grad; ctx.fill();
  ctx.beginPath();
  px.forEach((x, i) => i === 0 ? ctx.moveTo(x, py[i]) : ctx.lineTo(x, py[i]));
  ctx.strokeStyle = '#e8590c'; ctx.lineWidth = 2;
  ctx.lineJoin = 'round'; ctx.stroke();
  const lx = px[px.length - 1], ly = py[py.length - 1];
  ctx.beginPath(); ctx.arc(lx, ly, 4, 0, Math.PI * 2);
  ctx.fillStyle = '#e8590c'; ctx.fill();
  ctx.beginPath(); ctx.arc(lx, ly, 2, 0, Math.PI * 2);
  ctx.fillStyle = '#0f1114'; ctx.fill();
})();
"""

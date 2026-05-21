# Phase 4: Betting Intelligence — Diseño

## Resumen

Motor de detección de value bets que compara probabilidades del modelo XGBoost vs odds reales de bookmakers. Genera picks diarios con stake sugerido (1u-3u), trackea resultados automáticamente, y presenta todo en un dashboard de performance. Odds obtenidas de The Odds API (free tier, 500 req/mes).

**Filosofía:** Conservadora. Precisión sobre volumen. Solo recomendar cuando hay edge claro.

---

## 1. Odds Scraper

### Fuente: The Odds API (v4)

- Free tier: 500 requests/mes
- Endpoint: `GET /v4/sports/{sport}/odds`
- Mercados: `h2h` (1X2) + `totals` (Over/Under 2.5)
- BTTS no disponible en free tier
- Token en env var `ODDS_API_KEY`

### Mapeo de competiciones

| Division | The Odds API sport key |
|----------|----------------------|
| E0 | `soccer_epl` |
| SP1 | `soccer_spain_la_liga` |
| D1 | `soccer_germany_bundesliga` |
| I1 | `soccer_italy_serie_a` |
| F1 | `soccer_france_ligue_one` |
| EC | `soccer_uefa_champs_league` |
| WC | `soccer_fifa_world_cup` |

### Budget de requests

7 competiciones × `markets=h2h,totals` (ambos en una request) = 7 req/día × 30 = 210 req/mes. Margen de ~290 requests para re-runs o debugging.

### Módulo: `backend/etl/odds.py`

**`fetch_odds(sport_key, token)`** — llama la API, devuelve lista de eventos con odds. Parámetros: `regions=eu`, `markets=h2h,totals`, `oddsFormat=decimal`.

**`parse_odds(events, division, normalizer)`** — transforma respuesta de la API a lista de dicts con:
- `match_date`, `home_team`, `away_team` (normalizados con TeamNormalizer)
- `odd_home`, `odd_draw`, `odd_away` (mejor odd entre bookmakers, o Pinnacle si disponible)
- `odd_over25`, `odd_under25` (del mercado totals, punto 2.5)
- `bookmaker` (nombre del bookmaker de donde se tomó la odd)

**`update_match_odds(records)`** — actualiza columnas de odds en tabla `matches` para fixtures que aún no tienen resultado. Upsert por `(division, match_date, home_team, away_team)`.

**`run_odds_sync()`** — orquestador: itera las 7 competiciones (solo las que tienen fixtures activos), fetch + parse + update. Rate limit: `time.sleep(1)` entre calls.

### Matching de equipos

The Odds API usa nombres como "Arsenal", "Chelsea", "Real Madrid" — más limpios que football-data.org. Aún así, los normalizamos con TeamNormalizer. Se agregan alias necesarios a `data/team_mappings.json`.

### Script: `scripts/run_odds.py`

Lee `ODDS_API_KEY` de env, ejecuta `run_odds_sync()`.

---

## 2. Value Bet Engine

### Módulo: `backend/betting/value.py`

**Cálculo de edge por selección:**

```python
implied_prob = 1 / odd
edge = model_prob - implied_prob
expected_value = (model_prob * odd) - 1
```

### Clasificación de picks

| Stake | Condición | Significado |
|-------|-----------|-------------|
| 3u | edge > 0.10 AND confianza "alta" | Apuesta fuerte |
| 2u | edge > 0.07 AND confianza ≥ "media" | Apuesta media |
| 1u | edge > 0.05 | Apuesta mínima |
| Skip | edge ≤ 0.05 | Sin valor suficiente |

### Mercados evaluados

**1X2 (h2h):** Para cada partido, evalúa las 3 selecciones (H, D, A). Puede generar 0-3 picks por partido (en la práctica, rara vez más de 1 tiene edge).

**Over/Under 2.5 (totals):** Evalúa Over y Under. `prob_under25 = 1 - prob_over25`.

**BTTS:** Se publica probabilidad en la predicción pero no se genera pick (sin odds de mercado).

### Funciones

**`calculate_edge(model_prob, odd)`** — retorna dict con `edge`, `expected_value`, `implied_prob`.

**`generate_picks(predictions, matches_with_odds)`** — para cada predicción con odds disponibles, calcula edge en cada mercado, filtra por threshold, asigna stake. Retorna lista de picks.

**`classify_stake(edge, confidence)`** — aplica la tabla de clasificación.

### Script: `scripts/run_value_bets.py`

1. Lee predicciones de tabla `predictions`
2. Lee matches con odds (fixtures con `ft_result IS NULL` y odds no nulas)
3. Genera picks
4. Upsert a tabla `value_bets`

---

## 3. Performance Tracker

### Módulo: `backend/betting/tracker.py`

**`resolve_picks()`** — busca picks en `value_bets` donde `result IS NULL` y el partido ya tiene resultado en `matches`:

Para 1X2:
- Si `selection = 'H'` y `ft_result = 'H'` → win
- Si `selection = 'D'` y `ft_result = 'D'` → win
- Si `selection = 'A'` y `ft_result = 'A'` → win
- Otro → loss

Para Over/Under:
- `total_goals = ft_home_goals + ft_away_goals`
- Si `selection = 'Over'` y `total_goals > 2.5` → win
- Si `selection = 'Under'` y `total_goals <= 2.5` → win
- Otro → loss

**Cálculo de profit:**
- Win: `profit = (odd * stake) - stake = stake * (odd - 1)`
- Loss: `profit = -stake`

**`calculate_performance(division=None)`** — consulta `value_bets` resueltos y calcula:
- Profit total (unidades)
- ROI: `sum(profit) / sum(stake) * 100`
- Hit rate: `wins / total`
- Desglose por mercado (1X2, O/U)
- Desglose por stake (1u, 2u, 3u)
- Racha actual

### Script: `scripts/run_resolve_picks.py`

Ejecuta `resolve_picks()`. Log de picks resueltos.

---

## 4. Schema de Base de Datos

### Tabla `value_bets`

```sql
CREATE TABLE IF NOT EXISTS value_bets (
    id BIGSERIAL PRIMARY KEY,
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    division TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    model_prob REAL NOT NULL,
    implied_prob REAL NOT NULL,
    edge REAL NOT NULL,
    odd REAL NOT NULL,
    bookmaker TEXT,
    stake INTEGER NOT NULL,
    expected_value REAL NOT NULL,
    confidence TEXT NOT NULL,
    model_variant TEXT NOT NULL,
    result TEXT,
    profit REAL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    UNIQUE(match_date, home_team, away_team, market)
);

CREATE INDEX IF NOT EXISTS idx_value_bets_date ON value_bets(match_date);
CREATE INDEX IF NOT EXISTS idx_value_bets_result ON value_bets(result);
CREATE INDEX IF NOT EXISTS idx_value_bets_pending ON value_bets(result) WHERE result IS NULL;
```

**Columnas:**
- `market`: `'1x2_home'`, `'1x2_draw'`, `'1x2_away'`, `'over25'`, `'under25'`
- `selection`: `'H'`, `'D'`, `'A'`, `'Over'`, `'Under'`
- `result`: `NULL` (pendiente), `'win'`, `'loss'`
- `profit`: `NULL` hasta resolución, luego ± unidades
- `stake`: 1, 2, o 3

---

## 5. Dashboard — Página Value Bets

### Página: `dashboard/pages/5_value_bets.py`

Todo en español.

#### Sección 1: Picks Activos

- Título: "Picks del Día"
- Filtros: liga (selectbox), stake mínimo (selectbox: "Todos", "≥2u", "3u")
- Tabla con columnas: Fecha, Partido, Liga, Pick, Cuota, Edge %, Stake, EV
- Ordenada por fecha, luego edge descendente
- Badge de stake: 3u verde fuerte, 2u verde, 1u gris
- Si no hay picks: "No hay picks con valor para los próximos partidos"

#### Sección 2: Rendimiento Histórico

KPIs (`st.metric`):
- Profit Total (unidades, con delta vs mes anterior)
- ROI %
- Tasa de Acierto %
- Total Picks Resueltos

Tabla: P/L por mercado (1X2, Over/Under) con columnas Mercado, Picks, Ganados, ROI

Gráfico: Profit acumulado (plotly line chart, eje X = fecha, eje Y = profit en unidades)

Tabla: Últimos 20 picks resueltos con Fecha, Partido, Pick, Cuota, Stake, Resultado, Profit

### Componentes

| Archivo | Contenido |
|---------|-----------|
| `dashboard/components/value_bets.py` | `format_picks()`, `format_resolved()` — formateo de tablas |
| `dashboard/components/performance.py` | `profit_chart()`, `performance_kpis()` — gráficos y métricas |

---

## 6. Pipeline ETL Actualizado

### Nuevos steps en `.github/workflows/etl.yml`

Después de "Generate predictions":

```yaml
- name: Fetch current odds
  run: PYTHONPATH=. python scripts/run_odds.py
  env:
    ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
    SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
    DATABASE_URL: ${{ secrets.DATABASE_URL }}

- name: Generate value bets
  run: PYTHONPATH=. python scripts/run_value_bets.py
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
    SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
    DATABASE_URL: ${{ secrets.DATABASE_URL }}

- name: Resolve past picks
  run: PYTHONPATH=. python scripts/run_resolve_picks.py
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
    SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### Orden completo del pipeline

1. Checkout + setup Python
2. `run_etl.py` — descargar matches CSV
3. `run_fixtures.py` — fixtures de football-data.org
4. `run_understat.py` — xG data
5. `run_features.py` — generar features
6. Commit features
7. `run_training.py` — entrenar modelos + backtest
8. `run_predictions.py` — predicciones upcoming
9. `run_odds.py` — **odds actuales** (NEW)
10. `run_value_bets.py` — **generar picks** (NEW)
11. `run_resolve_picks.py` — **resolver picks pasados** (NEW)
12. Commit models + backtest results

---

## 7. Estructura de Archivos Nuevos

```
backend/betting/
├── __init__.py
├── value.py          (calculate_edge, generate_picks, classify_stake)
└── tracker.py        (resolve_picks, calculate_performance)

backend/etl/
└── odds.py           (fetch_odds, parse_odds, update_match_odds, run_odds_sync)

backend/db/
└── schema_value_bets.sql

scripts/
├── run_odds.py
├── run_value_bets.py
└── run_resolve_picks.py

dashboard/
├── components/
│   ├── value_bets.py     (format_picks, format_resolved)
│   └── performance.py    (profit_chart, performance_kpis)
└── pages/
    └── 5_value_bets.py
```

---

## Restricciones

- **Costo $0/mes:** The Odds API free tier (500 req/mes), 210 req/mes estimado
- **Conservador:** Solo picks con edge > 5%, stakes conservadores (1u-3u)
- **BTTS sin odds:** Se publica probabilidad pero no se genera pick
- **Resolución automática:** El ETL diario resuelve picks cuando los resultados están disponibles
- **Stack existente:** Python 3.13, Supabase, Streamlit, GitHub Actions
- **UI en español:** Todos los textos, labels, y badges en español

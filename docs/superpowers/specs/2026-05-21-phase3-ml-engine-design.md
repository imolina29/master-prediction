# Phase 3: ML Engine — Diseño

## Resumen

Motor de predicción basado en XGBoost para partidos de fútbol. Genera probabilidades para tres mercados (1X2, Over/Under 2.5, BTTS) usando features históricas de rendimiento por equipo. Usa dos variantes de modelo — premium (con xG) para las 5 ligas top, y base (sin xG) para el resto — con backtesting temporal riguroso para garantizar métricas reales sin data leakage.

**Filosofía:** Conservadora. Precisión sobre volumen. Solo publicar predicciones de alta confianza.

---

## 1. Preparación de Features a Nivel de Partido

### Problema

Las features actuales en `data/features/team_features.parquet` están a nivel de equipo-partido (201,408 filas). El modelo necesita una fila por partido con features de ambos equipos (home + away).

### Solución

Nuevo módulo `backend/ml/features.py` con función `build_match_features()`:

1. Leer features de Parquet
2. Separar en home/away por la columna `venue`
3. Join por `(division, match_date, team↔opponent)` para obtener una fila por partido
4. Agregar columnas del match de Supabase: `home_elo`, `away_elo`, `odd_home`, `odd_draw`, `odd_away`, `odd_over25`, `odd_under25`
5. Calcular `elo_diff = home_elo - away_elo`
6. Crear targets binarios: `result_H`, `result_D`, `result_A`, `over25`, `btts`

### Columnas del Feature Matrix (modelo premium)

**Home team (prefijo `home_`):**
- `home_goals_scored_avg`, `home_goals_conceded_avg`
- `home_xg_for_avg`, `home_xg_against_avg`, `home_xg_diff_avg`, `home_xg_overperformance`
- `home_shots_target_avg`, `home_corners_avg`
- `home_win_rate`, `home_draw_rate`
- `home_btts_rate`, `home_over25_rate`

**Away team (prefijo `away_`):**
- Mismas 12 columnas con prefijo `away_`

**Contexto del partido:**
- `home_elo`, `away_elo`, `elo_diff`

**Total: 27 features (premium), 19 features (base — sin las 4+4 columnas xG)**

### Modelo base vs premium

- **Premium:** Partidos donde AMBOS equipos tienen xG features (divisiones E0, SP1, D1, I1, F1, temporadas 2014+). ~37,086 filas disponibles → ~18,543 partidos.
- **Base:** TODOS los partidos (201,408 filas → ~100,704 partidos), usando solo features sin xG.

### Targets

| Target | Tipo | Columna origen | Codificación |
|--------|------|----------------|-------------|
| 1X2 | Multiclase (3) | `ft_result` | H=0, D=1, A=2 |
| Over/Under 2.5 | Binario | `ft_home_goals + ft_away_goals > 2.5` | 0/1 |
| BTTS | Binario | `ambos equipos anotaron` | 0/1 |

---

## 2. Modelos y Entrenamiento

### Arquitectura: 6 modelos XGBoost

| # | Modelo | Target | Features | Filas aprox |
|---|--------|--------|----------|-------------|
| 1 | `base_1x2` | 1X2 | 19 (sin xG) | ~100K |
| 2 | `base_over25` | O/U 2.5 | 19 | ~100K |
| 3 | `base_btts` | BTTS | 19 | ~100K |
| 4 | `premium_1x2` | 1X2 | 27 (con xG) | ~18K |
| 5 | `premium_over25` | O/U 2.5 | 27 | ~18K |
| 6 | `premium_btts` | BTTS | 27 | ~18K |

### Hiperparámetros iniciales

```python
BASE_PARAMS = {
    "max_depth": 6,
    "n_estimators": 300,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "eval_metric": "mlogloss",  # o "logloss" para binarios
    "random_state": 42,
}
```

- 1X2 usa `XGBClassifier(objective="multi:softprob", num_class=3, ...)`
- Over/Under y BTTS usan `XGBClassifier(objective="binary:logistic", ...)`

### Archivos

| Archivo | Responsabilidad |
|---------|-----------------|
| `backend/ml/config.py` | Constantes: features lists, params, paths |
| `backend/ml/features.py` | `build_match_features()` — join home+away+match data |
| `backend/ml/train.py` | `train_model()`, `train_all()` — entrenar y guardar .joblib |
| `backend/ml/predict.py` | `predict_match()`, `predict_upcoming()` — generar predicciones |
| `backend/ml/evaluate.py` | `walk_forward_backtest()`, `evaluate_fold()` — backtesting |

### Persistencia

- Modelos guardados en `models/{variant}_{target}.joblib` (ej: `models/premium_1x2.joblib`)
- Resultados de backtest en `data/backtest_results.json`
- Predicciones en tabla `predictions` de Supabase

---

## 3. Backtesting y Evaluación

### Walk-Forward Temporal (5 folds)

Sin data leakage: siempre entrenar en datos anteriores, testear en datos posteriores.

| Fold | Train | Test |
|------|-------|------|
| 1 | ≤ 2018/19 | 2019/20 |
| 2 | ≤ 2019/20 | 2020/21 |
| 3 | ≤ 2020/21 | 2021/22 |
| 4 | ≤ 2021/22 | 2022/23 |
| 5 | ≤ 2022/23 | 2023/24 |

Implementación: cortar por `match_date` usando julio como inicio de temporada (`YYYY-07-01`).

Para modelo premium: solo folds donde hay suficientes datos xG (folds 1-5 cubren 2014+, todos válidos).

### Métricas por fold

| Métrica | Target | Descripción |
|---------|--------|-------------|
| Accuracy | Todos | % predicciones correctas |
| Log Loss | Todos | Calidad de probabilidades calibradas |
| Brier Score | Binarios | Error cuadrático medio de probabilidades |
| Calibración | Todos | Bins de probabilidad predicha vs frecuencia real |
| ROI simulado | 1X2 | Simular apuestas flat (1u) cuando prob > implied prob de cuota |

### Simulación de ROI

Usando las columnas de cuotas existentes (`odd_home`, `odd_draw`, `odd_away`):

```
implied_prob = 1 / odd
value = model_prob - implied_prob
Si value > threshold (0.05): apostar 1 unidad
ROI = (ganancias - apuestas) / apuestas * 100
```

Threshold conservador: solo apostar cuando el modelo ve ≥5% de edge sobre la cuota.

### Output

`data/backtest_results.json`:
```json
{
  "base_1x2": {
    "folds": [
      {
        "fold": 1, "train_end": "2019-07-01", "test_season": "2019/20",
        "accuracy": 0.52, "log_loss": 0.98,
        "roi_pct": -2.3, "n_bets": 145, "n_test": 380
      }
    ],
    "mean_accuracy": 0.51, "mean_log_loss": 0.99, "mean_roi_pct": -1.5
  },
  "premium_1x2": { ... },
  ...
}
```

---

## 4. Predicciones y Pipeline

### Flujo de predicción

1. `predict_upcoming()` consulta partidos futuros (próximos 7 días) de Supabase
2. Para cada partido, construye feature vector usando las últimas features de cada equipo
3. Selecciona modelo: premium si ambos equipos están en liga top 5, base si no
4. Genera probabilidades para los 3 mercados
5. Clasifica confianza: **alta** (prob > 60%), **media** (prob > 45%), **baja** (≤ 45%)
6. Upsert a tabla `predictions` de Supabase

### Tabla `predictions` (Supabase)

```sql
CREATE TABLE predictions (
    id BIGSERIAL PRIMARY KEY,
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    division TEXT NOT NULL,
    model_variant TEXT NOT NULL,  -- 'base' o 'premium'
    prob_home REAL,
    prob_draw REAL,
    prob_away REAL,
    prob_over25 REAL,
    prob_btts REAL,
    predicted_result TEXT,  -- 'H', 'D', 'A'
    confidence TEXT,  -- 'alta', 'media', 'baja'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(match_date, home_team, away_team)
);

CREATE INDEX idx_predictions_date ON predictions(match_date);
CREATE INDEX idx_predictions_division ON predictions(division);
```

### Pipeline semanal (GitHub Actions)

Nuevo step en `.github/workflows/etl.yml`:

```yaml
- name: Train models
  run: PYTHONPATH=. python3 scripts/run_training.py

- name: Generate predictions
  run: PYTHONPATH=. python3 scripts/run_predictions.py --upcoming

- name: Auto-commit models
  run: |
    git add models/ data/backtest_results.json
    git diff --staged --quiet || git commit -m "chore: update models [skip ci]"
```

### Scripts

| Script | Función |
|--------|---------|
| `scripts/run_training.py` | Entrenar 6 modelos, guardar .joblib, correr backtest |
| `scripts/run_predictions.py` | `--upcoming` genera predicciones, `--backtest` corre evaluación |

---

## 5. Dashboard de Predicciones

### Página: `dashboard/pages/4_predicciones.py`

#### Sección 1: Predicciones Próximas

- Filtro por liga (selectbox)
- Filtro por confianza: alta, media, todas
- Tabla con columnas:
  - Fecha, Local, Visitante, Liga
  - Prob H / D / A (coloreadas: verde > 50%, amarillo 35-50%, rojo < 35%)
  - Resultado predicho (texto: "Local", "Empate", "Visitante")
  - O/U 2.5 (prob over, texto "Over"/"Under")
  - BTTS (prob, texto "Sí"/"No")
  - Confianza (badge: alta=verde, media=amarillo, baja=gris)
  - Modelo (base/premium)

#### Sección 2: Métricas del Modelo

- Cargadas desde `data/backtest_results.json`
- KPIs en métricas de Streamlit:
  - Accuracy promedio (1X2)
  - ROI simulado promedio
  - Total partidos evaluados
- Tabla de resultados por fold
- Gráfico de calibración: probabilidad predicha vs frecuencia real (plotly scatter)

### Componentes nuevos

| Archivo | Contenido |
|---------|-----------|
| `dashboard/components/predictions.py` | `predictions_table()` — formatea tabla con colores |
| `dashboard/components/metrics.py` | `calibration_chart()`, `backtest_summary()` |

---

## Restricciones

- **Costo $0/mes:** XGBoost es local, no requiere GPU ni APIs pagas
- **Sin data leakage:** shift(1) en features + walk-forward temporal en backtesting
- **Conservador:** Solo publicar predicciones de alta confianza en el dashboard por defecto
- **Reproducible:** `random_state=42` en todos los modelos
- **Stack existente:** Python 3.13, Supabase, DuckDB/Parquet, Streamlit, GitHub Actions

---

## Estructura de archivos nuevos

```
backend/ml/
├── __init__.py          (ya existe, vacío)
├── config.py            (constantes, paths, params)
├── features.py          (build_match_features)
├── train.py             (train_model, train_all)
├── predict.py           (predict_match, predict_upcoming)
└── evaluate.py          (walk_forward_backtest, evaluate_fold)

models/                  (6 archivos .joblib)

scripts/
├── run_training.py      (entrenar + backtest)
└── run_predictions.py   (predicciones upcoming)

dashboard/
├── components/
│   ├── predictions.py   (tabla de predicciones)
│   └── metrics.py       (gráficos de métricas)
└── pages/
    └── 4_predicciones.py

data/
└── backtest_results.json

backend/db/
└── schema_predictions.sql
```

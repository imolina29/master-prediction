# MASTER PREDICTION

## PRD — Plataforma de Betting Intelligence con IA

---

## 1. Visión General

**Master Prediction** es una plataforma SaaS de Betting Intelligence que combina análisis histórico, modelos predictivos de ML y detección de value bets para fútbol profesional.

**Filosofía**: conservador, basado en datos, low-cost, escalable.

---

## 2. Objetivo Principal

Construir un sistema que:

- Ingeste y normalice datos históricos de múltiples fuentes gratuitas
- Genere predicciones probabilísticas (1X2, Over/Under, BTTS, exact score)
- Detecte value bets comparando probabilidades internas vs odds de bookmakers
- Presente todo en dashboards analíticos claros
- Se actualice automáticamente vía pipelines diarios

---

## 3. Alcance Inicial (Competiciones)

- Top 5 ligas europeas: Premier League, La Liga, Serie A, Bundesliga, Ligue 1
- UEFA Champions League
- Mundiales FIFA masculinos
- Cobertura: temporadas históricas completas disponibles + actualización continua 25/26+

---

## 4. Fuentes de Datos

### Principales (gratuitas)

| Fuente | Uso | Cobertura |
|--------|-----|-----------|
| football-data.co.uk | Resultados + odds históricas | Ligas europeas desde ~1993 |
| StatsBomb Open Data | Eventos detallados, xG, tiros, pases | Competiciones selectas |
| FBref | Estadísticas avanzadas por equipo/jugador | Ligas top completas |
| Understat | xG, xA, shot data | Top 5 ligas desde 2014 |

### Complementarias

| Fuente | Uso |
|--------|-----|
| Club Football Match Data 2000-2025 (GitHub) | Resultados históricos masivos |
| Kaggle Football Datasets | Datasets variados para enriquecimiento |

### Estrategia Multi-Fuente

- Ingestión múltiple con normalización automática
- Reconciliación de IDs de equipos/jugadores (canonical IDs + fuzzy matching)
- Validación cruzada entre fuentes
- Ningún dataset gratuito tiene cobertura completa — la combinación es crítica

---

## 5. Stack Tecnológico (MVP — $0/mes)

### Backend

| Componente | Tecnología | Razón |
|------------|-----------|-------|
| Lenguaje | Python 3.12+ | Ecosistema ML/Data |
| Framework API | FastAPI | Rápido, async, tipado |
| Dashboard MVP | Streamlit | Dashboards funcionales en días |

### Base de Datos

| Componente | Tecnología | Razón |
|------------|-----------|-------|
| DB principal | Supabase (PostgreSQL free tier) | 500MB gratis, Postgres real, auth incluido |
| Data Lake | DuckDB + Parquet | Analytics rápido, cero costo, local |

### Infraestructura

| Componente | Tecnología | Razón |
|------------|-----------|-------|
| Hosting backend | Railway o Render (free tier) | $0/mes, deploy desde GitHub |
| Hosting dashboard | Streamlit Community Cloud | Gratis para repos públicos/privados |
| Automatización | GitHub Actions (cron) | 2000 min/mes gratis en repos privados |
| Storage | Supabase Storage o Cloudflare R2 | Gratis hasta 10GB |

### ML/IA

| Componente | Tecnología | Razón |
|------------|-----------|-------|
| Modelos principales | XGBoost, LightGBM, CatBoost | Probados en betting, interpretables |
| Modelos estadísticos | Poisson regression | Ideal para predicción de goles |
| Feature engineering | pandas, scikit-learn | Estándar de industria |

### Evolución futura (post-monetización)

| Cambio | Cuándo |
|--------|--------|
| Streamlit → Next.js + React + TypeScript | Cuando haya usuarios pagando |
| Supabase → PostgreSQL dedicado + TimescaleDB | Cuando >500MB de datos |
| Railway → GCP Cloud Run | Cuando necesite más compute |
| Agregar Redis para cache | Cuando la latencia importe |
| LSTM / Transformers ligeros | Cuando los modelos clásicos toquen techo |

---

## 6. Arquitectura General

```
┌─────────────────────┐
│  External Sources    │
│  (football-data,     │
│   StatsBomb, FBref)  │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  ETL Pipelines      │
│  (GitHub Actions)    │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Data Normalization  │
│  + Canonical IDs     │
└──────────┬──────────┘
           │
┌──────────▼──────────────┐
│  Supabase (PostgreSQL)   │
│  + DuckDB/Parquet Lake   │
└──────────┬──────────────┘
           │
┌──────────▼──────────┐
│  Feature Engineering │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  ML Prediction Core  │
│  (XGBoost, Poisson)  │
└──────────┬──────────┘
           │
┌──────────▼──────────────┐
│  Betting Intelligence    │
│  Engine (Value Bets)     │
└──────────┬──────────────┘
           │
┌──────────▼──────────┐
│  FastAPI + Streamlit │
│  (API + Dashboard)   │
└──────────────────────┘
```

---

## 7. Tipos de Predicción

| Tipo | Detalle |
|------|---------|
| 1X2 | Home win, Draw, Away win |
| Over/Under | 1.5, 2.5, 3.5 goles |
| BTTS | Ambos equipos anotan (sí/no) |
| Exact Score | Ej: 2-1, 1-1 |
| Props | Corners, tarjetas, tiros |
| Combinadas | Ej: Over 2.5 + BTTS |

---

## 8. Filosofía del Modelo

**Conservador**: prioriza precisión y consistencia sobre volumen de picks.

- NO picks exagerados ni probabilidades irreales
- Calibración rigurosa (probabilidades reflejan frecuencias reales)
- Evaluación histórica con métricas de betting (ROI, CLV, hit rate)
- Separación estricta train/validation/test temporal (evitar data leakage)

---

## 9. Value Bet Engine

Compara probabilidades internas del modelo vs odds de bookmakers:

```
Value = (Probability_model × Odds) - 1
```

Si Value > 0: el bookmaker ofrece una cuota superior a la probabilidad real estimada.

Solo recomienda bets con value positivo y confianza alta.

---

## 10. Feature Engineering

| Categoría | Features |
|-----------|----------|
| Equipo | Forma reciente, local/visitante, goles esperados (xG), racha |
| Jugadores | Disponibilidad, goles, xG contribution |
| Partido | Importancia, días de descanso, calendario |
| Históricas | Head-to-head, tendencias por liga/temporada |

---

## 11. Pipeline ETL

**Frecuencia**: diaria (vía GitHub Actions cron)

```
Extract → Validate → Normalize → Deduplicate → Store → Feature Generation → Model Update → Prediction Refresh
```

---

## 12. Dashboards (Streamlit MVP)

### Widgets principales

- Predicciones del día con nivel de confianza
- Value bets detectadas
- Métricas históricas del modelo (accuracy, ROI)
- Forma de equipos

### Visualizaciones

- xG charts
- Radar charts por equipo
- Tendencias de liga
- Historial de predicciones vs resultados reales

---

## 13. Estructura del Monorepo

```
master-prediction/
├── backend/
│   ├── api/            # FastAPI endpoints
│   ├── etl/            # Pipelines de ingestión
│   ├── ml/             # Modelos y training
│   ├── services/       # Lógica de negocio
│   ├── db/             # Schemas y migrations
│   └── utils/          # Helpers
├── dashboard/          # Streamlit app
├── data/               # .gitkeep only (datos en .gitignore)
├── models/             # .gitkeep only (modelos en .gitignore)
├── notebooks/          # Exploración y análisis
├── scripts/            # Scripts de setup y utilidades
├── docs/               # Documentación
├── .github/
│   └── workflows/      # GitHub Actions (ETL cron, CI)
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## 14. Roadmap por Fases

### FASE 1 — Foundation (2-3 semanas)

- Repositorio + estructura del monorepo
- Supabase setup (DB + Storage)
- ETL básico: football-data.co.uk → PostgreSQL
- Normalización de nombres de equipos
- GitHub Actions: pipeline de ingestión
- CI básico (linting, tests)

### FASE 2 — Historical Engine (3-5 semanas)

- Ingestión de todas las fuentes (StatsBomb, FBref, Understat)
- Sistema de canonical IDs + fuzzy matching
- Feature engineering base
- Dashboard Streamlit con datos históricos
- Validación cruzada de datos entre fuentes

### FASE 3 — ML Engine (4-6 semanas)

- Modelos base: XGBoost + Poisson
- Evaluación rigurosa con backtesting temporal
- Predicciones 1X2, Over/Under, BTTS
- Pipeline de re-entrenamiento automático
- Dashboard de predicciones

### FASE 4 — Betting Intelligence (3-4 semanas)

- Value Bet Engine
- Scraping/API de odds actuales
- Rankings de confianza
- Sistema de recomendaciones
- Historial de performance del modelo

### FASE 5 — SaaS Evolution (continuo)

- Migración a Next.js frontend
- Sistema de usuarios + autenticación
- Planes de suscripción
- API pública
- Escalado de infraestructura

---

## 15. KPIs

### Técnicos

- Model accuracy por tipo de predicción
- ETL success rate (>99%)
- Latencia de predicciones (<2s)

### Betting

- ROI simulado sobre histórico
- Hit rate por tipo de bet
- Calibración (predicted prob vs actual frequency)

---

## 16. Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Calidad inconsistente de datasets | Multi-fuente + validación cruzada |
| Sobreentrenamiento (overfitting) | Backtesting temporal estricto, regularización |
| Data leakage | Separación temporal train/val/test, nunca usar datos futuros |
| Sesgo temporal | Ventanas deslizantes, no mezclar épocas |
| Cambios en reglas/formato | Monitoreo de drift, re-entrenamiento |

---

## 17. Lo que NO hacemos en MVP

- Microservicios / Kubernetes
- Streaming / tiempo real
- Deep Learning complejo (LSTM, Transformers)
- Frontend elaborado (Next.js)
- Multi-tenant / roles de usuario
- Infraestructura costosa

---

## 18. Estrategia de Monetización (futuro)

1. **Freemium**: predicciones básicas gratis, detalladas de pago
2. **API**: acceso programático a predicciones (por request)
3. **Premium**: value bets, análisis avanzado, alertas
4. **Enterprise**: acceso a datos y modelos para casas de apuestas/medios

---

## 19. Costos

| Fase | Costo mensual |
|------|--------------|
| MVP (Fase 1-3) | $0 |
| Growth (Fase 4-5) | $5-30/mes |
| Scale | $50-200/mes |
| Enterprise | Variable según uso |

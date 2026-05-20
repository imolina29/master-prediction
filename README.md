# Master Prediction

Plataforma de Betting Intelligence basada en IA y analítica deportiva.

## Stack

- **Backend**: Python 3.12+ / FastAPI
- **Dashboard**: Streamlit
- **Database**: Supabase (PostgreSQL)
- **Data Lake**: DuckDB + Parquet
- **ML**: XGBoost, LightGBM, CatBoost, Poisson
- **Infra**: Railway/Render + GitHub Actions

## Estructura

```
master-prediction/
├── backend/        # API, ETL, ML, servicios
├── dashboard/      # Streamlit app
├── data/           # Datos (gitignored)
├── models/         # Modelos entrenados (gitignored)
├── notebooks/      # Exploración
├── scripts/        # Utilidades
├── docs/           # Documentación
└── .github/        # CI/CD workflows
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Documentación

- [PRD completo](docs/PRD.md)

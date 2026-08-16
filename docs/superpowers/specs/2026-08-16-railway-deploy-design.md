# Railway.app Deployment — Design Spec

## Goal

Deploy Master Prediction como un solo servicio en Railway.app, unificando la webapp NiceGUI y la API FastAPI en un unico proceso. Costo: $0-5/mes (credito gratuito de Railway). Sin cold starts, HTTPS automatico, auto-deploy desde GitHub.

## Why Railway

- NiceGUI usa WebSockets — descarta serverless (Vercel, Cloudflare Workers)
- Oracle Cloud Always Free ARM tiene problemas de capacidad (no se puede crear la VM)
- Railway soporta Docker, WebSockets, y tiene $5/mes de credito gratuito
- Sin cold starts (a diferencia de Render.com free tier que duerme la app tras 15 min)
- Deploy automatico desde GitHub push

## Architecture

```
Internet (HTTPS — Railway lo maneja)
   |
   v
[Railway Service — 1 proceso]
   |
   +-- NiceGUI webapp (puerto $PORT)
   |     - Sirve todas las paginas (11 rutas)
   |     - WebSocket para UI reactiva
   |     - Static files (banners)
   |
   +-- FastAPI API (embebido en la misma app)
   |     - POST /api/chat (asesor IA)
   |     - POST /api/performance (tendencias)
   |
   +-- Data local
         - data/features/team_features.parquet (6 MB)
         - data/features/national_*.json (194 KB)

[Supabase] — Base de datos existente (sin cambios)
```

Un solo proceso Python que corre NiceGUI + los routers de FastAPI. Railway asigna un puerto via variable `PORT` y maneja HTTPS/SSL automaticamente.

## Cambios al codigo

### 1. webapp/main.py — Montar API routers + leer PORT

Agregar antes de `ui.run()`:

```python
from backend.api.chat import router as chat_router
from backend.api.performance import router as perf_router

app.include_router(chat_router)
app.include_router(perf_router)
```

Modificar `ui.run()`:

```python
ui.run(
    title="Master Prediction",
    favicon="⚽",
    port=int(os.environ.get("PORT", 8080)),
    dark=True,
    storage_secret=os.environ.get("SUPABASE_KEY", "master-prediction-secret-key"),
    show=False,
    reload=False,
)
```

Nota: `reload=False` es importante en produccion para evitar el file watcher.

### 2. Dockerfile (raiz del repo)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt
COPY backend/ backend/
COPY webapp/ webapp/
COPY data/features/ data/features/
ENV PYTHONPATH=.
CMD ["python", "webapp/main.py"]
```

Railway autodetecta un `Dockerfile` en la raiz y lo usa para build. No necesita `railway.toml`, `Procfile`, ni `nixpacks`.

### 3. requirements-railway.txt

Solo las dependencias necesarias para el servicio unificado:

```
# Web framework
nicegui>=3.15.0
fastapi>=0.115.0
uvicorn>=0.32.0

# Database
supabase>=2.10.0

# Data
pandas>=2.2.0
duckdb>=1.1.0
pyarrow>=18.0.0

# Auth
bcrypt>=4.0.0

# HTTP client (para paginas que llaman APIs externas)
httpx>=0.28.0
requests>=2.32.0

# Utils
python-dotenv>=1.0.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
beautifulsoup4>=4.12.0
```

Excluye: xgboost, catboost, lightgbm, scikit-learn, streamlit, plotly, streamlit-authenticator, sqlalchemy, alembic, resend, ruff, pytest. Esto reduce la imagen ~50% y el RAM ~60%.

### 4. BACKEND_API_URL

Como la API ahora vive en el mismo proceso, `BACKEND_API_URL` se configura como `http://localhost:$PORT` o simplemente `http://localhost:8080`. Las paginas `asesor.py` y `tendencias.py` usan `os.environ.get("BACKEND_API_URL", "http://localhost:8081")` — en Railway se configura la variable para que apunte a si mismo.

Alternativamente, ya que todo corre en el mismo proceso, `BACKEND_API_URL` puede apuntar a `http://0.0.0.0:{PORT}` usando la variable PORT de Railway.

## Variables de entorno en Railway

Configurar en el dashboard de Railway (Settings → Variables):

| Variable | Valor |
|----------|-------|
| `SUPABASE_URL` | (misma que local) |
| `SUPABASE_KEY` | (misma que local) |
| `FOOTBALL_DATA_TOKEN` | (mismo que local) |
| `API_KEY_WEBAPP` | (mismo que local) |
| `BACKEND_API_URL` | `http://localhost:$PORT` |

`PORT` lo inyecta Railway automaticamente — no hay que configurarlo.

## Data files

El parquet (6 MB) y los JSON (194 KB) se incluyen en la imagen Docker via `COPY data/features/ data/features/`. Esto es aceptable porque:
- Son archivos pequenos (6.2 MB total)
- Railway no soporta volume mounts (es efimero)
- Los archivos se regeneran con el pipeline de features y se commitean (o se agregan al .gitignore y se copian manualmente)

Nota: `*.parquet` esta en `.gitignore`. Para que Railway tenga el archivo, hay dos opciones:
1. Quitar `*.parquet` del gitignore y commitear el archivo (6 MB, aceptable)
2. Generar el parquet en el build del Docker (mas complejo, innecesario)

La opcion 1 es la mas simple.

## Archivos que NO se modifican

- `docker/webapp.Dockerfile`, `docker/api.Dockerfile` — se quedan para Oracle Cloud futuro
- `docker-compose.yml`, `nginx/`, `scripts/` — se quedan para Oracle Cloud futuro
- Paginas de la webapp — sin cambios
- Logica de autenticacion — sin cambios
- `requirements.txt` original — sin cambios (se usa para desarrollo local)

## Deploy flow

1. Crear proyecto en Railway desde el dashboard
2. Conectar repo GitHub `imolina29/master-prediction`
3. Railway detecta el `Dockerfile`, hace build, y despliega
4. Configurar variables de entorno en el dashboard
5. Railway asigna un dominio tipo `master-prediction-production.up.railway.app`
6. (Opcional) Configurar dominio custom en el futuro

Updates: cada `git push` a la rama configurada triggers un auto-deploy.

## Estimacion de costos

- RAM: ~200 MB × 24h × 30d = ~144 GB-hours/mes
- CPU: ~0.1 vCPU promedio
- Railway pricing: $10/GB-RAM/mes → 0.2 GB × $10 = ~$2/mes
- Credito gratuito: $5/mes → **costo real: $0/mes**

## Fuera de alcance

- CI/CD custom (Railway ya hace auto-deploy)
- Dominio personalizado (se puede agregar despues)
- Monitoring avanzado (Railway tiene logs basicos)
- Horizontal scaling (no necesario)
- Pipeline de ML en Railway (se sigue corriendo local)

# Phase 6: Smart Platform — Diseño

## Resumen

Evolución de Master Prediction de herramienta personal a plataforma para grupo pequeño (5-20 usuarios). Cuatro pilares: alertas inteligentes via Telegram, dashboard de tendencias para análisis histórico de rendimiento, sistema multi-usuario con roles, y autenticación completa (dashboard + API + Telegram).

**Filosofía:** Mismo principio conservador — las alertas solo se disparan cuando hay señal clara, no ruido. Multi-usuario simple sin over-engineering (no es SaaS público).

**Restricciones:** $0/mes, Supabase free tier (500 MB), Streamlit Cloud free tier, The Odds API free tier.

---

## 1. Alertas Inteligentes (Telegram)

### Tipos de alerta

| Alerta | Trigger | Prioridad |
|--------|---------|-----------|
| Pick de alta confianza | Nuevo pick con stake = 3u | Alta |
| Racha positiva | 5+ picks ganados consecutivos | Media |
| Racha negativa | 3+ picks perdidos consecutivos | Media |
| Resumen semanal | Domingo 20:00 UTC | Baja |

### Formato de mensajes

**Pick de alta confianza:**
```
🔥 PICK PREMIUM

🟢🟢🟢 Arsenal vs Chelsea
Victoria Local · Cuota: 1.85 · Edge: +10.2%

📊 Modelo: 62% vs Mercado: 54%

👉 Ver análisis completo en el dashboard
[Abrir Dashboard]
```

**Racha positiva:**
```
🔥 Racha de 5 aciertos!

Profit acumulado en racha: +8.3u
ROI en racha: +42%

Últimos picks:
✅ Arsenal ML +0.85u
✅ Barcelona O2.5 +0.92u
...

[Abrir Dashboard]
```

**Resumen semanal:**
```
📊 Master Prediction — Semana 21

Picks: 12 | ✅ 8 | ❌ 4
Profit: +3.2u | ROI: +15.8%

Mejor liga: Premier League (+2.1u)
Mejor mercado: Over 2.5 (+1.8u)

[Ver Detalle]
```

### Módulo: `backend/notifications/alerts.py`

**`check_high_confidence_picks(picks)`** — Filtra picks con stake=3 que no hayan sido notificados aún. Retorna lista.

**`check_streaks(resolved)`** — Analiza los últimos N picks resueltos en orden cronológico. Retorna `{"type": "win"|"loss", "count": int, "picks": [...]}` si hay racha >= 5 wins o >= 3 losses. None si no hay racha activa.

**`build_weekly_summary(resolved, start_date, end_date)`** — Calcula métricas de la semana: profit, ROI, picks por liga, picks por mercado. Retorna dict con todos los datos para el mensaje.

**`send_alert(notifier, alert_type, data)`** — Dispatcher que formatea el mensaje según tipo y lo envía via TelegramNotifier.

### Script: `scripts/run_alerts.py`

- Se ejecuta después de `run_value_bets.py` y `run_resolve_picks.py` en el pipeline
- Chequea: picks de alta confianza nuevos, rachas, y si es domingo el resumen semanal
- Usa un campo `alerted` (boolean) en `value_bets` para no re-notificar picks ya alertados

### Cambio en tabla `value_bets`

Agregar columna `alerted BOOLEAN DEFAULT FALSE` para rastrear qué picks ya fueron notificados como alerta premium.

### Pipeline

Nuevo step en `etl.yml` después de `run_notifications.py`:
```yaml
- name: Check and send smart alerts
  run: PYTHONPATH=. python scripts/run_alerts.py
```

El resumen semanal requiere un cron adicional o una condición `if domingo` dentro del script (preferible para no agregar otro workflow).

---

## 2. Dashboard de Tendencias

### Nueva página: `dashboard/pages/7_tendencias.py`

Análisis histórico del rendimiento del modelo con visualizaciones avanzadas.

### Secciones

**2.1 Rendimiento por Liga**
- Heatmap (plotly): filas = ligas, columnas = meses, color = profit
- Tabla resumen: liga, total picks, profit, ROI, hit_rate, mejor mes
- Permite identificar en qué ligas el modelo rinde mejor

**2.2 Rendimiento por Mercado**
- Barras agrupadas: 1x2 vs Over/Under vs (futuro: BTTS)
- Por cada mercado: profit, ROI, distribución de stakes
- Comparación mensual entre mercados

**2.3 Evolución Temporal**
- Gráfico de línea: profit acumulado por mes (últimos 6 meses)
- Overlay con número de picks por mes (volumen vs rentabilidad)
- Moving average de hit_rate (ventana de 20 picks)

**2.4 Análisis de Stakes**
- Rendimiento segmentado por nivel de stake (1u, 2u, 3u)
- ¿Los picks de alta confianza realmente rinden más?
- Tabla: stake, picks, wins, profit, ROI

### Componente: `dashboard/components/trends.py`

**`league_heatmap(resolved)`** — Plotly heatmap con profit por liga/mes.

**`market_comparison_chart(resolved)`** — Barras agrupadas por mercado.

**`profit_timeline(resolved)`** — Línea temporal de profit acumulado con overlay de volumen.

**`stake_analysis_table(resolved)`** — DataFrame con rendimiento por nivel de stake.

### Datos

Todos los datos vienen de la tabla `value_bets` (picks resueltos). No se necesitan tablas nuevas. Se usa `st.cache_data(ttl=3600)` para cachear.

---

## 3. Sistema Multi-Usuario

### Roles

| Rol | Dashboard | API | Telegram | Gestión usuarios |
|-----|-----------|-----|----------|-----------------|
| admin | Full access | Full access | Recibe alertas | Puede crear/editar usuarios |
| viewer | Solo lectura | Solo lectura | Recibe picks diarios | — |

### Almacenamiento de usuarios

**Opción elegida: `st.secrets` + archivo TOML**

Para un grupo de 5-20 usuarios, no necesitamos una tabla en Supabase. Usamos el mismo mecanismo que ya tenemos con streamlit-authenticator, expandiendo el TOML de secrets:

```toml
[credentials]
[credentials.ivan]
name = "Ivan Molina"
email = "ivan@example.com"
password = "$2b$12$hash..."
role = "admin"

[credentials.amigo1]
name = "Amigo 1"
email = "amigo1@example.com"
password = "$2b$12$hash..."
role = "viewer"
```

**Justificación:** 
- No introduce dependencias nuevas
- Los passwords se hashean con bcrypt (ya lo hace streamlit-authenticator)
- Para 5-20 usuarios es perfectamente manejable
- Se administra directamente desde Streamlit Cloud secrets

### Gestión de usuarios (admin)

**Nueva página: `dashboard/pages/8_admin.py`** (solo visible para admins)

- Lista de usuarios actuales (sin mostrar passwords)
- Formulario para generar hash de password para nuevo usuario
- Instrucciones para agregar en Streamlit Cloud secrets
- No permite crear usuarios dinámicamente (limitación de st.secrets ser read-only)

**Alternativa futura:** Si el grupo crece más de 20, migrar a tabla `users` en Supabase con JWT propio. Pero no lo hacemos ahora (YAGNI).

### Módulo: `dashboard/auth.py` (modificar existente)

**Cambios:**
- `check_auth()` retorna el rol del usuario además del bool (o `None` si no autenticado)
- Nuevo helper `get_current_user()` que retorna `{"username": str, "name": str, "role": str}`
- Nuevo helper `require_admin()` que verifica rol admin o muestra error
- Sidebar muestra rol del usuario junto al nombre

### Visibilidad por rol

- Páginas 1-7: Visibles para todos los roles
- Página 8 (Admin): Solo admin
- En el sidebar, la página Admin solo aparece si el rol es admin

---

## 4. Autenticación Completa

### 4.1 Dashboard (ya implementado)

- streamlit-authenticator con sesiones de 30 minutos
- Cookie-based con TOML secrets
- Ya está funcionando

### 4.2 API (FastAPI)

**Nuevo módulo: `backend/api/auth.py`**

Autenticación API con API keys simples (no JWT completo — YAGNI para grupo pequeño).

```python
API_KEYS = {
    "pipeline": os.environ.get("API_KEY_PIPELINE", ""),
    "telegram": os.environ.get("API_KEY_TELEGRAM", ""),
}
```

**`verify_api_key(key)`** — Valida que el API key exista en el dict. Retorna el nombre del cliente.

**Dependency para FastAPI:**
```python
async def get_api_client(x_api_key: str = Header(...)):
    client = verify_api_key(x_api_key)
    if not client:
        raise HTTPException(401)
    return client
```

**Alcance:** Protege cualquier endpoint futuro de la API. Actualmente no hay endpoints expuestos (todo se ejecuta via scripts), pero queda listo para cuando se expongan.

**Nota:** Los scripts del pipeline (GitHub Actions) no necesitan auth — corren en el servidor con acceso directo a Supabase via service key. La API auth es para cuando se expongan endpoints HTTP.

### 4.3 Telegram

**Nuevo módulo: `backend/notifications/auth_telegram.py`**

**Validación de chat_id:**
- Lista de chat_ids autorizados en env var `TELEGRAM_AUTHORIZED_CHATS` (comma-separated)
- El bot solo responde a mensajes de chats autorizados
- Si alguien no autorizado intenta interactuar, responde con mensaje genérico

**Webhook vs Polling:**
Para grupo pequeño, no necesitamos webhook (requiere servidor HTTP permanente). Los mensajes se envían push-only desde el pipeline. La validación de chat_id aplica si en el futuro se agrega interactividad (bot commands).

```python
AUTHORIZED_CHATS = set(
    os.environ.get("TELEGRAM_AUTHORIZED_CHATS", "").split(",")
)

def is_authorized_chat(chat_id: str) -> bool:
    return str(chat_id) in AUTHORIZED_CHATS
```

**Para el pipeline actual:** `TelegramNotifier` ya envía a un `TELEGRAM_CHAT_ID` específico. Para multi-usuario, el notifier iterará sobre todos los chat_ids autorizados:

**Cambio en `TelegramNotifier`:**
```python
def __init__(self, token=None, chat_ids=None):
    self.token = token or os.environ["TELEGRAM_BOT_TOKEN"]
    self.chat_ids = chat_ids or os.environ.get(
        "TELEGRAM_AUTHORIZED_CHATS", os.environ.get("TELEGRAM_CHAT_ID", "")
    ).split(",")
```

**`send_to_all(text, reply_markup)`** — Envía el mismo mensaje a todos los chat_ids autorizados.

**Env vars nuevas:**
- `TELEGRAM_AUTHORIZED_CHATS`: Lista de chat_ids separados por coma (reemplaza `TELEGRAM_CHAT_ID` para multi-usuario)

---

## 5. Configuración y Env Vars

### Nuevas env vars

| Variable | Descripción | Dónde |
|----------|-------------|-------|
| `TELEGRAM_AUTHORIZED_CHATS` | Chat IDs autorizados (comma-separated) | GitHub Secrets + Streamlit Secrets |
| `API_KEY_PIPELINE` | API key para el pipeline (futuro) | GitHub Secrets |
| `API_KEY_TELEGRAM` | API key para Telegram bot (futuro) | GitHub Secrets |

### Cambios en Streamlit Secrets

Agregar `role` a cada usuario en `[credentials]`.

---

## 6. Archivos Nuevos y Modificados

### Nuevos
- `backend/notifications/alerts.py` — Motor de alertas inteligentes
- `scripts/run_alerts.py` — Script de alertas para pipeline
- `dashboard/pages/7_tendencias.py` — Página de tendencias
- `dashboard/components/trends.py` — Componentes de visualización de tendencias
- `dashboard/pages/8_admin.py` — Panel de administración
- `backend/api/auth.py` — Auth para API
- `backend/notifications/auth_telegram.py` — Auth para Telegram

### Modificados
- `dashboard/auth.py` — Agregar roles, `get_current_user()`, `require_admin()`
- `backend/notifications/telegram.py` — Multi-chat support, `send_to_all()`
- `.github/workflows/etl.yml` — Agregar step de alertas
- `backend/db/schema_value_bets.sql` — Agregar columna `alerted`
- `scripts/run_notifications.py` — Usar `send_to_all()` en lugar de chat_id único

### Tests nuevos
- `tests/test_alerts.py` — Tests para check_streaks, check_high_confidence_picks
- `tests/test_trends.py` — Tests para funciones de cálculo de tendencias
- `tests/test_auth_roles.py` — Tests para sistema de roles
- `tests/test_telegram_multi.py` — Tests para multi-chat delivery

---

## 7. Orden de Implementación

1. **Multi-usuario + Roles** — Base para todo lo demás (define quién accede a qué)
2. **Telegram multi-chat** — Permite enviar a múltiples usuarios
3. **Alertas inteligentes** — Requiere multi-chat + tabla alerted
4. **Dashboard de tendencias** — Independiente, solo necesita datos existentes
5. **Panel admin** — Requiere roles implementados
6. **Auth API** — Preparación futura, no bloquea funcionalidad actual
7. **Auth Telegram** — Preparación futura para interactividad del bot

---

## 8. Consideraciones

### Limites de Supabase free tier
- 500 MB storage. La tabla `value_bets` con campo `alerted` no agrega overhead significativo.
- No hay límite práctico de rows para nuestro volumen (~50 picks/día máx).

### Limites de Telegram
- 30 mensajes/segundo por bot (no es problema para 5-20 usuarios)
- Si se envía a todos los chats, iterar con `time.sleep(0.1)` entre envíos

### Seguridad
- Passwords hasheados con bcrypt (streamlit-authenticator lo maneja)
- API keys en env vars, nunca en código
- Sesiones de 30 minutos ya implementadas
- No se almacenan datos sensibles en el cliente

### Escalabilidad futura
- Si el grupo crece > 20 usuarios: migrar credentials a tabla Supabase
- Si se necesitan más roles: agregar tabla de permisos
- Si se necesita interactividad en Telegram: webhook + commands handler
- Ninguno de estos cambios requiere re-arquitectura

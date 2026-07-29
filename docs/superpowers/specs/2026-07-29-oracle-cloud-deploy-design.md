# Oracle Cloud Always Free Deployment — Design Spec

## Goal

Deploy Master Prediction (NiceGUI webapp + FastAPI backend) publicly en internet con costo $0/mes usando Oracle Cloud Always Free Tier, Docker Compose, y DuckDNS para dominio gratuito con SSL.

## Why Oracle Cloud

- **Always Free Tier real:** VM ARM (Ampere A1) con hasta 4 OCPUs + 24GB RAM, gratis para siempre (no trial de 12 meses)
- NiceGUI usa WebSockets, lo que descarta serverless (Vercel, Cloudflare Workers, Netlify)
- Alternativas gratuitas (Fly.io, Render, Railway) tienen limits de horas o cold starts
- Oracle es la unica opcion que da una VM completa sin cargo mensual

## Architecture

```
Internet
   |
   v
[Oracle ARM VM - 2 OCPU, 12GB RAM, Ubuntu 22.04]
   |
   +-- Docker Compose
       |
       +-- nginx (puerto 80/443)
       |     - Reverse proxy + SSL termination
       |     - HTTP -> HTTPS redirect
       |     - /api/* -> api:8081
       |     - /* -> webapp:8080 (con WebSocket upgrade)
       |
       +-- webapp (NiceGUI, puerto 8080)
       |     - Python 3.12-slim
       |     - PYTHONPATH=. python webapp/main.py
       |
       +-- api (FastAPI, puerto 8081)
       |     - Python 3.12-slim
       |     - uvicorn backend.api.main:app --host 0.0.0.0 --port 8081
       |
       +-- certbot (Let's Encrypt SSL)
             - Solo corre para obtener/renovar certificados

[DuckDNS] -> IP publica estatica de la VM
[Supabase] -> Base de datos existente (sin migrar nada)
```

## Section 1: Oracle Cloud Infrastructure

### VM Specs
- Shape: VM.Standard.A1.Flex (ARM Ampere)
- Config: 2 OCPUs, 12GB RAM (dentro del free tier de 4 OCPU / 24GB)
- OS: Ubuntu 22.04 LTS (Canonical)
- Storage: 50GB boot volume (free tier permite hasta 200GB)
- IP: Static public IP (1 gratis en Always Free)

### Network / Firewall
- VCN con subnet publica
- Security List: abrir puertos 80 (HTTP), 443 (HTTPS), 22 (SSH)
- iptables en la VM: mismo set de puertos

### Costo
- VM: $0 (Always Free)
- IP publica: $0 (1 gratis)
- Storage: $0 (50GB dentro de 200GB free)
- Egress: 10TB/mes gratis (mas que suficiente)

## Section 2: Docker Files & Compose

### docker/webapp.Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=.
CMD ["python", "webapp/main.py"]
```

### docker/api.Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=.
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8081"]
```

### docker-compose.yml
```yaml
version: "3.8"
services:
  webapp:
    build:
      context: .
      dockerfile: docker/webapp.Dockerfile
    env_file: .env
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    env_file: .env
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      - certbot-etc:/etc/letsencrypt
      - certbot-www:/var/www/certbot
    depends_on:
      - webapp
      - api
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-www:/var/www/certbot

volumes:
  certbot-etc:
  certbot-www:
```

### nginx/nginx.conf
```nginx
server {
    listen 80;
    server_name masterprediction.duckdns.org;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name masterprediction.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/masterprediction.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/masterprediction.duckdns.org/privkey.pem;

    location /api/ {
        proxy_pass http://api:8081/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://webapp:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Nota: El `proxy_http_version 1.1` y headers `Upgrade`/`Connection` son obligatorios para que los WebSockets de NiceGUI funcionen correctamente.

## Section 3: Setup Inicial y Deploy

### Pasos manuales (una sola vez)
1. Crear cuenta en Oracle Cloud (requiere tarjeta pero no cobra)
2. Crear VM ARM Always Free (Ubuntu 22.04, 2 OCPU, 12GB RAM)
3. Asignar IP publica estatica
4. Configurar Security List: puertos 80, 443, 22
5. Registrar subdominio en DuckDNS y apuntar a la IP publica
6. SSH a la VM, instalar Docker + Docker Compose
7. Clonar el repo privado (SSH key o token)
8. Copiar `.env` a la VM
9. Ejecutar `docker compose up -d --build`
10. Obtener primer certificado SSL con certbot

### Deploy continuo
```bash
ssh vm "cd master-prediction && git pull && docker compose up -d --build"
```

Un solo comando. Se puede meter en `scripts/deploy.sh` para conveniencia.

### Variables de entorno (.env en la VM)
Las mismas variables que ya existen localmente:
- `SUPABASE_URL` — misma instancia Supabase (no se migra nada)
- `SUPABASE_KEY`
- `FOOTBALL_DATA_TOKEN`
- `API_KEY_WEBAPP`
- `BACKEND_API_URL=http://api:8081` (cambia de localhost al nombre del container Docker)

### Lo que NO se necesita
- No migrar Supabase — la VM se conecta al mismo Supabase existente
- No instalar Python en la VM — todo corre en Docker
- No CI/CD automatico por ahora — se agrega despues si se quiere

## Section 4: DuckDNS + SSL + Mantenimiento

### DuckDNS (DNS gratuito)
- Registrar subdominio en duckdns.org (ej: `masterprediction.duckdns.org`)
- Cron job en la VM actualiza la IP cada 5 minutos:
  ```
  */5 * * * * curl -s "https://www.duckdns.org/update?domains=masterprediction&token=TU_TOKEN"
  ```

### SSL con Let's Encrypt (certbot)
- Primer certificado:
  ```bash
  docker compose run certbot certonly --webroot -w /var/www/certbot -d masterprediction.duckdns.org
  ```
- Renovacion automatica cada 60 dias via cron:
  ```
  0 3 1 */2 * cd /home/ubuntu/master-prediction && docker compose run certbot renew && docker compose restart nginx
  ```

### Monitoreo basico
- Health check con cron: `curl -sf https://masterprediction.duckdns.org/login || echo "DOWN"`
- Docker restart policy: `restart: unless-stopped` en todos los containers
- Logs: `docker compose logs -f webapp` para debug

### Backups
- No necesarios para la VM — todo el codigo esta en GitHub, los datos en Supabase
- Si la VM muere: crear otra, clonar repo, copiar .env, `docker compose up -d`

## Prerequisitos antes de implementar

1. **requirements.txt** — agregar dependencias de NiceGUI que actualmente no estan listadas
2. **Cuenta Oracle Cloud** — creada con tarjeta (no cobra)
3. **Cuenta DuckDNS** — registro con GitHub/Google

## Fuera de alcance (para despues)
- CI/CD automatico (GitHub Actions -> deploy)
- Dominio personalizado (requiere compra)
- Monitoring avanzado (Uptime Robot, etc.)
- CDN / cache layer
- Horizontal scaling (no necesario por ahora)

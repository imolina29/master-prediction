#!/usr/bin/env bash
# SSL certificate renewal — run via cron every 2 months:
#   0 3 1 */2 * /home/ubuntu/master-prediction/scripts/renew-ssl.sh >> /var/log/ssl-renew.log 2>&1

set -euo pipefail

PROJECT_DIR="${1:-/home/ubuntu/master-prediction}"

cd "$PROJECT_DIR"
docker compose run --rm certbot renew
docker compose restart nginx

echo "$(date): SSL renewal complete"

#!/usr/bin/env bash
# DuckDNS IP update — run via cron every 5 minutes.
# cron does not pass shell/env vars to jobs, so DUCKDNS_TOKEN must be
# inlined directly in the crontab entry:
#   */5 * * * * DUCKDNS_TOKEN=your_token_here /home/ubuntu/master-prediction/scripts/duckdns-update.sh >> /var/log/duckdns.log 2>&1

DUCKDNS_TOKEN="${DUCKDNS_TOKEN:-}"
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN:-masterprediction}"

if [ -z "$DUCKDNS_TOKEN" ]; then
    echo "$(date): DUCKDNS_TOKEN not set"
    exit 1
fi

curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&verbose=true"
echo ""

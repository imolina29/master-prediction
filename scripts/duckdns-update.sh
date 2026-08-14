#!/usr/bin/env bash
# DuckDNS IP update — run via cron every 5 minutes:
#   */5 * * * * /home/ubuntu/master-prediction/scripts/duckdns-update.sh >> /var/log/duckdns.log 2>&1

DUCKDNS_TOKEN="${DUCKDNS_TOKEN:-}"
DUCKDNS_DOMAIN="${DUCKDNS_DOMAIN:-masterprediction}"

if [ -z "$DUCKDNS_TOKEN" ]; then
    echo "$(date): DUCKDNS_TOKEN not set"
    exit 1
fi

curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&verbose=true"
echo ""

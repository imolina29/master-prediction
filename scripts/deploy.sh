#!/usr/bin/env bash
set -euo pipefail

# Deploy Master Prediction to the Oracle Cloud VM.
# Usage: ./scripts/deploy.sh [ssh-host]
# Example: ./scripts/deploy.sh ubuntu@129.153.x.x

HOST="${1:-mp-vm}"
REMOTE_DIR="master-prediction"

echo "Deploying to $HOST..."
ssh "$HOST" "cd $REMOTE_DIR && git pull && docker compose up -d --build"
echo "Deploy complete. Check: https://masterprediction.duckdns.org"

#!/usr/bin/env bash
set -euo pipefail

# One-time setup for Oracle Cloud ARM VM (Ubuntu 22.04).
# Run this via SSH on the VM after first boot.

echo "=== Updating system ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== Installing Docker ==="
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== Adding user to docker group ==="
sudo usermod -aG docker "$USER"

echo "=== Opening firewall ports ==="
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Log out and back in (for docker group)"
echo "  2. Clone repo: git clone git@github.com:imolina29/master-prediction.git"
echo "  3. Copy .env to master-prediction/.env"
echo "  4. Generate features parquet: cd master-prediction && python scripts/run_features.py"
echo "  5. Start: cd master-prediction && docker compose up -d --build"
echo "  6. Get SSL cert: docker compose run certbot certonly --webroot -w /var/www/certbot -d masterprediction.duckdns.org"
echo "  7. Restart nginx: docker compose restart nginx"

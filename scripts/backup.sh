#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
TS=$(date +%Y%m%d_%H%M%S)
docker compose exec -T db pg_dump -U escolhaom -d escolhaom | gzip > "backups/escolhaom_${TS}.sql.gz"
echo "Backup: backups/escolhaom_${TS}.sql.gz"

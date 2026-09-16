#!/usr/bin/env bash
set -euo pipefail
if [ $# -ne 1 ]; then echo "Uso: $0 backups/arquivo.sql.gz"; exit 1; fi
cd "$(dirname "$0")/.."
gunzip -c "$1" | docker compose exec -T db psql -U escolhaom -d escolhaom

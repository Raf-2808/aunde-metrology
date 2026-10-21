#!/usr/bin/env bash
set -euo pipefail
umask 077
cel="${1:-backupy}"
mkdir -p -- "$cel"
plik="$cel/metrologia-$(date -u +%Y%m%dT%H%M%SZ).dump"
tymczasowy="$plik.partial"
trap 'rm -f -- "$tymczasowy"' EXIT
docker compose exec -T baza sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$tymczasowy"
docker compose exec -T baza pg_restore --list < "$tymczasowy" > /dev/null
mv -- "$tymczasowy" "$plik"
printf 'Zapisano backup: %s\n' "$plik"

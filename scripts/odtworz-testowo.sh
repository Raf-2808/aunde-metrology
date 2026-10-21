#!/usr/bin/env bash
set -euo pipefail
plik="${1:?Podaj plik backupu}"
baza="${2:?Podaj nowa nazwe bazy metrologia_restore_...}"
if [[ ! "$baza" =~ ^metrologia_restore_[a-zA-Z0-9_]+$ ]]; then
  printf 'Dozwolona jest tylko nowa testowa baza metrologia_restore_...\n' >&2
  exit 1
fi
# createdb zakończy się błędem, jeśli baza już istnieje. Skrypt niczego nie nadpisuje.
docker compose exec -T baza sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" createdb -U "$POSTGRES_USER" "$1"' sh "$baza"
docker compose exec -T baza sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error' sh "$baza" < "$plik"
docker compose exec -T baza sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$1" -c "SELECT count(*) AS przyrzady FROM przyrzady; SELECT count(*) AS odczyty FROM odczyty_qr;"' sh "$baza"

#!/bin/sh
set -eu
umask 077
mkdir -p /backups
while true; do
  target="/backups/lims-$(date -u +%Y%m%dT%H%M%SZ).dump"
  if pg_dump -Fc -f "$target.tmp"; then
    mv "$target.tmp" "$target"
    find /backups -name 'lims-*.dump' -mtime +30 -delete
  else
    echo 'BACKUP FAILED' >&2
    rm -f "$target.tmp"
  fi
  sleep 86400
done

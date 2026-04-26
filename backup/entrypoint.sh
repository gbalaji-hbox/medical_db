#!/bin/sh
set -e

mkdir -p /backups

do_backup() {
  STAMP=$(date +%Y%m%d_%H%M%S)
  sqlite3 /data/api.db ".backup /backups/api_${STAMP}.db"
  find /backups -name "*.db" -mtime +7 -delete
  echo "[$(date)] Backup completed: api_${STAMP}.db"
}

echo "Backup sidecar started — daily at 02:00, retaining 7 days"

while true; do
  if [ "$(date +%H:%M)" = "02:00" ]; then
    do_backup
    sleep 61   # skip past the current minute before re-checking
  else
    sleep 60
  fi
done

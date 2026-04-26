#!/bin/sh
set -e

mkdir -p /backups

cat > /usr/local/bin/do-backup.sh << 'EOF'
#!/bin/sh
STAMP=$(date +%Y%m%d_%H%M%S)
sqlite3 /data/api.db ".backup /backups/api_${STAMP}.db"
find /backups -name "*.db" -mtime +7 -delete
echo "[$(date)] Backup completed: api_${STAMP}.db"
EOF

chmod +x /usr/local/bin/do-backup.sh

# Run daily at 02:00
echo '0 2 * * * /usr/local/bin/do-backup.sh >> /var/log/backup.log 2>&1' | crontab -

echo "Backup sidecar started — daily at 02:00, retaining 7 days"
exec crond -f -l 6

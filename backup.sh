#!/bin/bash
# Freqtrade Production Backup Script for Coolify
# Usage: Run this script daily via cron job

set -e

# Configuration
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/freqtrade/backups"
CONTAINER_NAME="freqtrade-production"
S3_BUCKET="${S3_BUCKET_NAME}"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "📦 Starting Freqtrade backup at $(date)"

# Backup SQLite database
echo "💾 Backing up trading database..."
docker exec "$CONTAINER_NAME" sqlite3 /freqtrade/user_data/tradesv3.sqlite ".backup /tmp/backup_$DATE.sqlite"
docker cp "$CONTAINER_NAME:/tmp/backup_$DATE.sqlite" "$BACKUP_DIR/tradesv3_$DATE.sqlite"
docker exec "$CONTAINER_NAME" rm "/tmp/backup_$DATE.sqlite"

# Backup user data (logs, strategies, etc.)
echo "📁 Backing up user data..."
docker exec "$CONTAINER_NAME" tar -czf "/tmp/user_data_$DATE.tar.gz" -C /freqtrade user_data
docker cp "$CONTAINER_NAME:/tmp/user_data_$DATE.tar.gz" "$BACKUP_DIR/"
docker exec "$CONTAINER_NAME" rm "/tmp/user_data_$DATE.tar.gz"

# Backup configuration
echo "⚙️ Backing up configuration..."
docker exec "$CONTAINER_NAME" cp /freqtrade/config_production.json "/tmp/config_$DATE.json"
docker cp "$CONTAINER_NAME:/tmp/config_$DATE.json" "$BACKUP_DIR/"
docker exec "$CONTAINER_NAME" rm "/tmp/config_$DATE.json"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
    echo "☁️ Uploading to S3..."
    aws s3 cp "$BACKUP_DIR/tradesv3_$DATE.sqlite" "s3://$S3_BUCKET/freqtrade-backups/" --storage-class STANDARD_IA
    aws s3 cp "$BACKUP_DIR/user_data_$DATE.tar.gz" "s3://$S3_BUCKET/freqtrade-backups/" --storage-class STANDARD_IA
    aws s3 cp "$BACKUP_DIR/config_$DATE.json" "s3://$S3_BUCKET/freqtrade-backups/" --storage-class STANDARD_IA
fi

# Cleanup old local backups
echo "🧹 Cleaning up old backups..."
find "$BACKUP_DIR" -name "tradesv3_*.sqlite" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "user_data_*.tar.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "config_*.json" -mtime +$RETENTION_DAYS -delete

# Create backup report
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "✅ Backup completed successfully at $(date)"
echo "📊 Backup directory size: $BACKUP_SIZE"
echo "📁 Files backed up:"
ls -lah "$BACKUP_DIR" | tail -n 5

echo "🎉 Freqtrade backup completed successfully!"

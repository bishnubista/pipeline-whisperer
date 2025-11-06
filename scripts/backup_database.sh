#!/bin/bash
# Database backup script for Pipeline Whisperer
# Supports both PostgreSQL and SQLite

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Determine database type
if [[ "$DATABASE_URL" == sqlite* ]]; then
    # SQLite backup
    log_info "Starting SQLite backup..."

    DB_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite:///||')
    BACKUP_FILE="$BACKUP_DIR/pipeline_sqlite_$TIMESTAMP.db"

    if [ -f "$DB_PATH" ]; then
        cp "$DB_PATH" "$BACKUP_FILE"
        gzip "$BACKUP_FILE"
        log_info "SQLite backup created: $BACKUP_FILE.gz"
    else
        log_error "SQLite database not found at: $DB_PATH"
        exit 1
    fi

elif [[ "$DATABASE_URL" == postgresql* ]]; then
    # PostgreSQL backup
    log_info "Starting PostgreSQL backup..."

    # Extract connection details
    DB_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
    DB_PASS=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')

    BACKUP_FILE="$BACKUP_DIR/pipeline_postgres_$TIMESTAMP.sql"

    export PGPASSWORD="$DB_PASS"
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --no-owner --no-acl --clean --if-exists \
        -f "$BACKUP_FILE"

    gzip "$BACKUP_FILE"
    unset PGPASSWORD

    log_info "PostgreSQL backup created: $BACKUP_FILE.gz"

else
    log_error "Unsupported database type: $DATABASE_URL"
    exit 1
fi

# Clean up old backups
log_info "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "pipeline_*.gz" -mtime +$RETENTION_DAYS -delete

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
log_info "Backup size: $BACKUP_SIZE"

# List recent backups
log_info "Recent backups:"
ls -lh "$BACKUP_DIR" | grep "pipeline_" | tail -5

log_info "Backup completed successfully!"

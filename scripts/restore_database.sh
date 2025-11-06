#!/bin/bash
# Database restore script for Pipeline Whisperer

set -euo pipefail

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

# Check arguments
if [ $# -lt 1 ]; then
    log_error "Usage: $0 <backup_file>"
    log_info "Example: $0 backups/pipeline_postgres_20250106_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Validate backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Confirm restore
log_warn "WARNING: This will replace the current database!"
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Restore cancelled."
    exit 0
fi

# Decompress if needed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    log_info "Decompressing backup file..."
    TEMP_FILE="${BACKUP_FILE%.gz}"
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    RESTORE_FILE="$TEMP_FILE"
else
    RESTORE_FILE="$BACKUP_FILE"
fi

# Determine database type and restore
if [[ "$DATABASE_URL" == sqlite* ]]; then
    # SQLite restore
    log_info "Restoring SQLite database..."

    DB_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite:///||')

    # Backup current database
    if [ -f "$DB_PATH" ]; then
        cp "$DB_PATH" "$DB_PATH.backup_$(date +%Y%m%d_%H%M%S)"
        log_info "Current database backed up"
    fi

    # Restore
    cp "$RESTORE_FILE" "$DB_PATH"
    log_info "SQLite database restored successfully"

elif [[ "$DATABASE_URL" == postgresql* ]]; then
    # PostgreSQL restore
    log_info "Restoring PostgreSQL database..."

    # Extract connection details
    DB_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
    DB_PASS=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')

    export PGPASSWORD="$DB_PASS"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -f "$RESTORE_FILE"
    unset PGPASSWORD

    log_info "PostgreSQL database restored successfully"

else
    log_error "Unsupported database type: $DATABASE_URL"
    exit 1
fi

# Cleanup temporary file
if [[ "$BACKUP_FILE" == *.gz ]]; then
    rm -f "$TEMP_FILE"
fi

log_info "Restore completed successfully!"
log_warn "Remember to restart the application"

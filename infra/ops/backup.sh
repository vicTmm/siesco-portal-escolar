#!/usr/bin/env bash
set -euo pipefail
: "${BACKUP_DATABASE_URL:?Defina BACKUP_DATABASE_URL com usuário de backup autorizado}"
: "${BACKUP_DIR:?Defina um diretório privado para os backups}"
umask 077
mkdir -p "$BACKUP_DIR"
backup_file="$BACKUP_DIR/portal-$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump --dbname="${BACKUP_DATABASE_URL/postgresql+psycopg/postgresql}" --format=custom --no-owner --file="$backup_file"
pg_restore --list "$backup_file" >/dev/null
printf 'Backup criado: %s\n' "$backup_file"

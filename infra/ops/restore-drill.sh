#!/usr/bin/env bash
set -euo pipefail
: "${RESTORE_DATABASE_URL:?Defina RESTORE_DATABASE_URL apontando para banco vazio portal_restore}"
: "${BACKUP_FILE:?Defina BACKUP_FILE}"
restore_url="${RESTORE_DATABASE_URL/postgresql+psycopg/postgresql}"
restore_db=$(psql "$restore_url" -Atc 'SELECT current_database()')
if [[ "$restore_db" != "portal_restore" ]]; then
  printf 'Restauração de ensaio exige banco dedicado portal_restore.\n' >&2
  exit 1
fi
restore_tables=$(psql "$restore_url" -Atc "SELECT count(*) FROM pg_tables WHERE schemaname='public'")
if [[ "$restore_tables" != "0" ]]; then
  printf 'Banco de ensaio precisa estar vazio; nenhum dado foi removido.\n' >&2
  exit 1
fi
pg_restore --dbname="$restore_url" --no-owner --exit-on-error --single-transaction "$BACKUP_FILE"
psql "$restore_url" -v ON_ERROR_STOP=1 -c 'SELECT version_num FROM alembic_version' -c 'SELECT count(*) AS institutions FROM institutions'

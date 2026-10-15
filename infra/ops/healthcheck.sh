#!/usr/bin/env bash
set -euo pipefail
: "${PORTAL_URL:?Defina PORTAL_URL}"
: "${API_HEALTH_URL:?Defina API_HEALTH_URL}"
curl --fail --silent --show-error --max-time 10 "$PORTAL_URL" >/dev/null
curl --fail --silent --show-error --max-time 10 "$API_HEALTH_URL" >/dev/null
printf 'Portal e API disponíveis em %s\n' "$(date -u +%FT%TZ)"

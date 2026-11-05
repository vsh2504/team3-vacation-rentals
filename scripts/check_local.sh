#!/usr/bin/env bash
# Backwards-compatible local diagnostic.
#
# The original PR 15 checklist lived here. It now delegates to
# health_local.sh, which checks PostgreSQL, direct API health, the search
# endpoint, the Vite dev server, and the Vite /api proxy — with actionable
# failure messages and a non-zero exit code.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/health_local.sh" "$@"

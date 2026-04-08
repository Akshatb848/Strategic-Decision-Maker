#!/bin/sh
# ASIS n8n entrypoint — imports workflows on first start, then runs n8n.
set -e

WORKFLOWS_DIR="/workflows"
IMPORTED_FLAG="/home/node/.n8n/.workflows_imported"

# Import workflows once (skip if already imported — flag file exists)
if [ -d "$WORKFLOWS_DIR" ] && [ ! -f "$IMPORTED_FLAG" ]; then
  echo "[asis-n8n] Importing workflows from $WORKFLOWS_DIR ..."
  IMPORT_ERRORS=0
  for f in "$WORKFLOWS_DIR"/*.json; do
    [ -f "$f" ] || continue
    BASENAME=$(basename "$f")
    if n8n import:workflow --input="$f" 2>&1; then
      echo "[asis-n8n] ✓ Imported: $BASENAME"
    else
      echo "[asis-n8n] ✗ Failed:   $BASENAME (non-fatal)"
      IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
    fi
  done
  touch "$IMPORTED_FLAG"
  echo "[asis-n8n] Workflow import complete (errors: $IMPORT_ERRORS)."
else
  echo "[asis-n8n] Skipping workflow import (already done or no /workflows dir)."
fi

# Start n8n
echo "[asis-n8n] Starting n8n ..."
exec n8n start

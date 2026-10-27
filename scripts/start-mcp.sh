#!/bin/bash
set -euo pipefail
umask 077
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
data_dir="${WHATSAPP_DATA_DIR:-/Volumes/sd1tb/agent-outputs/whatsapp-mcp}"
export WHATSAPP_API_TOKEN_FILE="$data_dir/api-token"
export WHATSAPP_MESSAGES_DB="$data_dir/runtime/store/messages.db"
export WHATSAPP_API_BASE_URL="http://127.0.0.1:8080/api"
export PYTHONDONTWRITEBYTECODE=1
export PATH="/opt/homebrew/bin:$PATH"
exec "$data_dir/venv/bin/python" "$repo_dir/whatsapp-mcp-server/main.py"

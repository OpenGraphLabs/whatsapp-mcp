#!/bin/bash
set -euo pipefail
umask 077
data_dir="${WHATSAPP_DATA_DIR:-/Volumes/sd1tb/agent-outputs/whatsapp-mcp}"
if [[ ! -d "$data_dir/runtime" ]]; then
  echo "WhatsApp data directory is unavailable: $data_dir/runtime" >&2
  exit 1
fi
export WHATSAPP_API_TOKEN_FILE="$data_dir/api-token"
export WHATSAPP_QR_PATH="$data_dir/pairing-qr.png"
cd "$data_dir/runtime"
exec "$data_dir/bin/whatsapp-bridge"

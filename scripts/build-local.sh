#!/bin/bash
set -euo pipefail
umask 077
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
data_dir="${WHATSAPP_DATA_DIR:-/Volumes/sd1tb/agent-outputs/whatsapp-mcp}"
if [[ -z "${WHATSAPP_DATA_DIR:-}" && ! -d /Volumes/sd1tb ]]; then
  echo 'Mount /Volumes/sd1tb before building.' >&2
  exit 1
fi
mkdir -p "$data_dir/bin" "$data_dir/runtime" "$data_dir/cache"
chmod 700 "$data_dir" "$data_dir/runtime"
python3 - "$data_dir/api-token" <<'PYTOKEN'
import os, secrets, sys
try:
    fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    pass
else:
    with os.fdopen(fd, "w") as token_file:
        token_file.write(secrets.token_hex(32) + "\n")
PYTOKEN
export GOCACHE="$data_dir/cache/go-build"
export GOMODCACHE="$data_dir/cache/go-mod"
export UV_CACHE_DIR="$data_dir/cache/uv"
export UV_PROJECT_ENVIRONMENT="$data_dir/venv"
uv sync --frozen --project "$repo_dir/whatsapp-mcp-server"
cd "$repo_dir/whatsapp-bridge"
go build -o "$data_dir/bin/whatsapp-bridge" .

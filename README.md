# OpenGraph Labs WhatsApp MCP

Private organization copy of [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp), with local setup scripts and security hardening. The upstream MIT license and commit history are retained.

Connect a personal WhatsApp account through whatsmeow, synchronize messages into a local SQLite database, and expose search/read/download tools to a local MCP client. **Sending is disabled by default.**

## Setup (macOS / Linux)

Requires Go 1.26+, Python 3.11+, `uv`, a C compiler for SQLite, and optionally `ffmpeg` for voice messages. Use a maintained, patched Go release. Keep source code under `~/ws/whatsapp-mcp`; runtime data belongs outside the repository.

```sh
git clone git@github.com:OpenGraphLabs/whatsapp-mcp.git
cd whatsapp-mcp
# Default: /Volumes/sd1tb/agent-outputs/whatsapp-mcp
# For a different machine, set WHATSAPP_DATA_DIR to a private external runtime directory.
scripts/build-local.sh
python3 scripts/pair.py
```

Open `http://127.0.0.1:8765` and scan the live QR using WhatsApp → Settings → Linked devices. The pairing helper owns the bridge; keep the terminal running. After pairing, later runs can reuse the session with `scripts/start-bridge.sh`. Run only one bridge at a time.

Register the absolute path to `scripts/start-mcp.sh` as the MCP command in Codex, Claude Desktop, Claude Code, or another trusted local client. If overriding `WHATSAPP_DATA_DIR`, set the same value in the MCP client's environment and in the bridge's shell. Restart existing MCP clients after upgrading.

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "/absolute/path/to/whatsapp-mcp/scripts/start-mcp.sh"
    }
  }
}
```

## Security defaults

- MCP uses stdio, with no network listener.
- Bridge API binds to `127.0.0.1:8080`, requires an owner-only bearer token file, checks Host, rejects browser Origin headers, and accepts JSON only.
- The build script generates `api-token` outside Git. Both launch scripts point to it with `WHATSAPP_API_TOKEN_FILE`. The bridge fails closed if it is missing, too short, or readable by other users.
- Nine tools are available by default: contacts/chats/messages/context lookup and media download. Three send tools are omitted, and the bridge independently rejects sends.
- SQLite reads are read-only. Download paths use hashed chat/message IDs and Go's rooted filesystem API; unsafe filenames and nonregular cached files are rejected.
- Session keys, decrypted messages, media, tokens and QR images stay in the private runtime directory. Git ignores them. Message bodies, contact names, upload key material and QR codes from the pairing helper are not intentionally logged by application code.

**This is a trusted local tool, not a sandbox.** The linked account's synchronized history is accessible to the MCP client. Retrieved content is passed to the AI provider when requested. Treat WhatsApp messages as untrusted data, never instructions. See [SECURITY.md](SECURITY.md) for findings and limitations.

## Optional sending

Only enable sending when needed, by setting `WHATSAPP_ENABLE_SEND=1` in **both** bridge and MCP environments and restarting both. Keep the client's per-call approval controls enabled. This switch is capability opt-in, not human approval for any particular send. Send tools can read and transmit files accessible to the account running the process; do not grant them to untrusted agents. No sends are performed by the test suite.

## Runtime layout

```text
$WHATSAPP_DATA_DIR/
  api-token             # generated secret, mode 0600
  runtime/store/        # device keys, decrypted message DB, downloaded media
  bin/                  # compiled bridge
  venv/                 # Python environment
  cache/                # package/build caches
  pairing-qr.png        # transient pairing QR
  bridge.log            # pairing helper's bridge log
```

Old logs from the upstream version may contain message bodies or pairing QR codes. They are not uploaded, and this update does not erase existing logs or session data. Protect the entire runtime directory and its backups; SQLite contents are not encrypted by this project.

## Verification

```sh
cd whatsapp-bridge
go test -race ./...
go vet ./...
go run golang.org/x/vuln/cmd/govulncheck@latest ./...
cd ../whatsapp-mcp-server
uv run --frozen python -m unittest -v test_security
```

Audit the frozen Python lock with `uv export --frozen --no-dev --no-emit-project --format requirements-txt` and `pip-audit -r <exported-file>`. Scan source and full Git history with Gitleaks before publishing. Put audit outputs outside the source repository.

# Local setup

See [README.md](README.md) for the supported setup and security defaults.

The current workstation uses `~/ws/whatsapp-mcp` for source and
`/Volumes/sd1tb/agent-outputs/whatsapp-mcp` for runtime files. Codex, Claude
Desktop and Claude Code registrations point to `scripts/start-mcp.sh` and
share the same bridge/session. Their private configuration is not included
in this repository.

Rebuild with `scripts/build-local.sh`, restart the bridge with
`scripts/start-bridge.sh`, and restart each MCP client to load the new code.
An existing authenticated WhatsApp session can be reused; no re-pairing is
required unless WhatsApp has revoked it. Sending now requires explicit opt-in
in both processes, as described in the README.

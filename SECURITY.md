# Security review — 2026-10-27

Scope: organization publication of the local WhatsApp MCP installation, upstream history, current Go/Python source, launch/pairing scripts, dependency locks, and local file permissions. This is a focused code review with regression tests and known-vulnerability scanners, not a penetration-test certification.

## Findings and remediation

| Finding | Impact | Resolution |
| --- | --- | --- |
| Unauthenticated localhost bridge | A caller able to reach the endpoint could send messages or transmit a local file. Loopback alone is not authorization. | Mandatory private bearer token, Host check, Origin rejection, JSON requirement, request size/time limits, redirects/proxies disabled in Python client. |
| Sending enabled for every MCP client | Untrusted chat text could influence an agent to transmit data. | Send tools hidden by default; Python and Go independently reject sending without explicit opt-in. Human approval remains a client responsibility. |
| Sender-controlled download filename | Directory traversal, file overwrite, or filename collisions across messages. | Reject path separators/special filenames; hash chat and message IDs; use `os.Root` and exclusive file creation; reject symlink/nonregular cached files. |
| Sensitive application logs | Incoming/history message bodies, contact names and uploaded media key material were printed. | Remove those logs. Pairing helper writes QR only to a private transient file; existing legacy log permissions tightened without deleting data. |
| Incomplete Git exclusions | SQLite sidecars, session/media directories and generated QR/token files could be added accidentally. | Expand `.gitignore`; inspect tracked file inventory and scan full history plus final source. No actual WhatsApp runtime data is included. |
| Old Python dependency lock | Initial pip-audit flagged 10 packages (54 advisory records, including duplicate IDs). | Refresh frozen lock; keep MCP on compatible 1.x and verify tool discovery. |

## Verification

- Go race-enabled security regression tests and `go vet`.
- Real stdio MCP initialization and read-only `list_chats` / `list_messages` calls passed against the existing local database; message content was not saved to review artifacts.
- MCP dependency upgrade required disabling structured output validation to preserve the upstream text/dataclass results; covered by a serialization regression test.
- Python tests: nine default tools; all sends denied before I/O; remote API URL rejected; bearer authentication with proxies/redirects disabled.
- Go tests: missing/wrong token, hostile Host/Origin, non-JSON requests, disabled sends, allowed authenticated mock requests, traversal/symlink rejection, isolated cached media and token permissions.
- `pip-audit` after update: no known vulnerabilities reported.
- `govulncheck`: no vulnerable symbols or imported packages reported. One module-level advisory remains: [GO-2026-5932](https://pkg.go.dev/vuln/GO-2026-5932), the unmaintained `golang.org/x/crypto/openpgp` package. This application does not import that package; no fixed module version is listed.
- Gitleaks history/source scans and a tracked-file inventory check before publication. Audit artifacts remain in the external runtime output directory, not Git.

## Remaining boundaries

- Local databases contain decrypted messages and device credentials. The runtime directory must remain private; use encrypted storage/backups where appropriate. Same-user malware or a compromised MCP host can read it. The HTTP token does not protect against a process already running as that user.
- Read tools expose synchronized history for the whole linked account, with no per-chat ACL. Only connect trusted clients and understand their AI-provider data handling.
- If sending is explicitly enabled, send tools can transmit arbitrary readable local files. Require per-call human approval in the client. There is no independent interactive approval broker in this server.
- Attachments are untrusted files. They are not scanned for malware, and resource use depends on media size. Optional ffmpeg conversion has additional parser risk. Do not execute downloaded attachments.
- Old log contents are not retroactively sanitized. The pairing viewer is available to local processes while running; close it when pairing is no longer needed.
- Dependency scans cover published advisories, not every possible vulnerability or supply-chain compromise. Repeat scans when updating.
- No real message/file send was used for validation. The fixes do not prove absence of all security issues.

Report new findings privately to the OpenGraph Labs repository administrators. Do not attach chats, session databases, tokens or pairing QR images to issues.

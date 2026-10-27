#!/usr/bin/env python3
"""Local live QR viewer; owns one bridge, retries expired pairing up to five times."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA = Path(os.environ.get("WHATSAPP_DATA_DIR", "/Volumes/sd1tb/agent-outputs/whatsapp-mcp"))
REPO = Path(__file__).resolve().parent.parent
QR = DATA / "pairing-qr.png"
state = {"attempt": 0, "running": False, "done": False}
stop = threading.Event()

HTML = '''<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WhatsApp 연결</title>
<style>body{font:18px system-ui;max-width:650px;margin:40px auto;padding:0 24px;background:#f6faf8;color:#12392a}h1{font-size:30px}img{width:min(100%,480px);image-rendering:pixelated;background:white;border:16px solid white;border-radius:12px;box-sizing:border-box}#status{font-weight:600}small{color:#52665b}</style>
<h1>WhatsApp 연결</h1>
<p>휴대폰 WhatsApp → 설정 → 연결된 기기 → 기기 연결에서 스캔하세요.</p>
<p id="status" role="status">새 QR 준비 중…</p>
<img id="qr" alt="WhatsApp 연결 QR" hidden>
<p><small>QR은 자동으로 갱신됩니다. 이전에 저장한 QR 이미지는 사용하지 마세요.</small></p>
<script>
let version = null;
async function refresh(){
 try {
  const s = await (await fetch('/status',{cache:'no-store'})).json();
  const img = document.getElementById('qr');
  document.getElementById('status').textContent = s.paired ? '인증 완료! 이 화면을 닫아도 됩니다.' : s.done ? '인증 대기가 끝났습니다. 새 인증 세션을 시작해 주세요.' : s.qr ? '스캔 대기 중 · 최신 QR 자동 갱신' : '새 QR 준비 중…';
  img.hidden = s.paired || !s.qr || s.done;
  if (!img.hidden && version !== s.version){version=s.version;img.src='/qr?v='+version;}
 } catch(e){document.getElementById('status').textContent='인증 서버와 연결이 끊겼습니다.';document.getElementById('qr').hidden=true;}
}
refresh();setInterval(refresh,1000);
</script></html>'''

def paired():
    db = DATA / 'runtime/store/whatsapp.db'
    if not db.exists():
        return False
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=1) as conn:
        return bool(conn.execute('SELECT count(*) FROM whatsmeow_device').fetchone()[0])

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in ('127.0.0.1:8765', 'localhost:8765'):
            self.send_error(403)
            return
        route = self.path.split('?')[0]
        if route == '/':
            body, kind = HTML.encode(), 'text/html; charset=utf-8'
        elif route == '/status':
            try:
                version = QR.stat().st_mtime_ns if state['running'] else None
            except FileNotFoundError:
                version = None
            body = json.dumps({**state, 'paired': paired(), 'qr': version is not None,
                               'version': str(version)}).encode()
            kind = 'application/json'
        elif route == '/qr' and state['running']:
            try:
                body = QR.read_bytes()
            except FileNotFoundError:
                self.send_error(404)
                return
            kind = 'image/png'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

def run_bridge():
    for attempt in range(1, 6):
        if stop.is_set():
            break
        QR.unlink(missing_ok=True)
        state.update(attempt=attempt, running=True)
        with (DATA / 'bridge.log').open('a') as log:
            os.fchmod(log.fileno(), 0o600)
            child = subprocess.Popen([str(REPO / 'scripts/start-bridge.sh')], stdout=log, stderr=log)
            try:
                while child.poll() is None and not stop.wait(1):
                    pass
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
        state['running'] = False
        QR.unlink(missing_ok=True)
        if stop.is_set() or paired():
            break
        if stop.wait(3):
            break
    state['done'] = True

if __name__ == '__main__':
    os.umask(0o077)
    if not (DATA / 'runtime').is_dir():
        raise SystemExit('Mount the data volume and build the bridge first.')
    # Bind before starting the bridge, so a second viewer cannot launch another one.
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    worker = threading.Thread(target=run_bridge, daemon=True)
    worker.start()
    print('Open http://127.0.0.1:8765 — QR refreshes automatically.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        worker.join(timeout=7)

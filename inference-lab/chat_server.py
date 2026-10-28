"""Local-only chat UI; proxy streaming requests without exposing the API key."""
import os
import json
import pathlib
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
BASE = os.environ.get('VLLM_BASE_URL', 'https://YOUR_POD_ID-8000.proxy.runpod.net').rstrip('/')
MODEL = 'Qwen/Qwen3-8B'
HOST, PORT = '127.0.0.1', 8765

def headers():
    values = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines() if '=' in line)
    return {'Authorization': 'Bearer ' + values['VLLM_API_KEY'],
            'Content-Type': 'application/json', 'User-Agent': 'inference-lab/1.0'}

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, kind='application/json'):
        data = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/':
            self.reply(200, (ROOT / 'chat.html').read_text(), 'text/html; charset=utf-8')
        elif self.path == '/api/status':
            try:
                req = urllib.request.Request(BASE + '/v1/models', headers=headers())
                with urllib.request.urlopen(req, timeout=8) as response:
                    models = json.load(response)
                ready = any(m['id'] == MODEL for m in models.get('data', []))
                self.reply(200, json.dumps({'ready': ready}))
            except (OSError, ValueError):
                self.reply(200, json.dumps({'ready': False}))
        else:
            self.reply(404, '{"error":"Not found"}')

    def do_POST(self):
        if self.path != '/api/chat':
            return self.reply(404, '{"error":"Not found"}')
        # Reject cross-site browser requests; this server is deliberately loopback-only.
        if self.headers.get('Origin') not in (None, f'http://{HOST}:{PORT}', f'http://localhost:{PORT}'):
            return self.reply(403, '{"error":"Origin rejected"}')
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply(415, '{"error":"JSON required"}')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 32000:
                raise ValueError()
            body = json.loads(self.rfile.read(size))
            messages = body['messages']
            if not isinstance(messages, list) or not 1 <= len(messages) <= 40:
                raise ValueError()
            if any(not isinstance(m, dict) or m.get('role') not in ('user', 'assistant')
                   or not isinstance(m.get('content'), str) or not m['content'].strip() for m in messages):
                raise ValueError()
            max_tokens = body.get('max_tokens', 512)
            if type(max_tokens) is not int or max_tokens not in (512, 1024):
                return self.reply(400, '{"error":"Choose a response limit of 512 or 1024 tokens."}')
            payload = {'model': MODEL, 'messages': messages, 'max_tokens': max_tokens,
                       'temperature': 0.7, 'stream': True,
                       'stream_options': {'include_usage': True},
                       'chat_template_kwargs': {'enable_thinking': False}}
        except (ValueError, KeyError, TypeError):
            return self.reply(400, '{"error":"Invalid or oversized conversation. Start a new chat."}')
        try:
            req = urllib.request.Request(BASE + '/v1/chat/completions',
                                         data=json.dumps(payload).encode(), headers=headers())
            upstream = urllib.request.urlopen(req, timeout=90)
        except urllib.error.HTTPError as error:
            message = ('Conversation exceeds model context. Start a new chat.' if error.code == 400
                       else 'Model unavailable. Start the Runpod Pod and wait for it to load.')
            return self.reply(502, json.dumps({'error': message}))
        except (OSError, ValueError):
            return self.reply(502, '{"error":"Cannot reach model. Check the Pod and local .env configuration."}')
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            with upstream:
                for line in upstream:
                    self.wfile.write(line)
                    self.wfile.flush()
        except (OSError, TimeoutError):
            # Browser treats a stream without [DONE] as interrupted.
            pass

if __name__ == '__main__':
    print(f'Chat lab: http://{HOST}:{PORT}', flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

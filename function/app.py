"""
A tiny "serverless-style function": one HTTP endpoint, /invoke, that does a small piece
of work and returns JSON. Standard library only.

It also reports how long its own initialisation took (from the first line of this
module running to the server being ready), so the benchmark can split a cold start into
"container start" and "app init".
"""

import time

module_start = time.perf_counter()

import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

LISTEN_PORT = int(os.environ.get("PORT", "8080"))


def handle_invocation():
    # A small, fixed amount of real work (hash 64 KB), so the function is not empty.
    payload = b"x" * 65536
    return {"sha256_prefix": hashlib.sha256(payload).hexdigest()[:12]}


class FunctionHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # Send each response as one packet with TCP_NODELAY, to avoid a ~40 ms
    # Nagle/delayed-ACK stall that Python's http.server otherwise causes.
    wbufsize = -1
    disable_nagle_algorithm = True

    def do_GET(self):
        if self.path != "/invoke":
            body = b'{"error": "not found"}'
            self.send_response(404)
        else:
            result = handle_invocation()
            result["init_ms"] = INIT_MS
            body = json.dumps(result).encode("utf-8")
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        return  # no per-request logging (it would add noise)


server = HTTPServer(("0.0.0.0", LISTEN_PORT), FunctionHandler)
INIT_MS = round((time.perf_counter() - module_start) * 1000, 3)
print(f"function ready on port {LISTEN_PORT}, init took {INIT_MS} ms", flush=True)
server.serve_forever()

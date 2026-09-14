from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from integrations.unified_cli_gateway.providers.mock_provider import make_response
from integrations.unified_cli_gateway.routes.formats import route_to_format
from scripts.harness_lib import read_yaml


class GatewayHandler(BaseHTTPRequestHandler):
    config: dict[str, Any] = {}

    def log_message(self, format, *args):  # noqa: A002
        return

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not self.config.get("require_api_key"):
            return True
        env_name = str(self.config.get("api_key_env") or "AGENTMETER_API_KEY")
        expected = os.environ.get(env_name)
        if not expected:
            return False
        header = self.headers.get("Authorization") or ""
        return header == f"Bearer {expected}" or header == expected

    def do_GET(self):  # noqa: N802
        if self.path in {"/health", "/v1/health"}:
            self._send(200, {"ok": True, "service": "unified_cli_gateway"})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if not self._authorized():
            self._send(401, {"error": "unauthorized"})
            return
        length = int(self.headers.get("Content-Length") or "0")
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        response_format = route_to_format(self.path)
        self._send(200, make_response(payload, response_format=response_format))


def serve(config_path: str | Path) -> None:
    config = read_yaml(config_path)
    GatewayHandler.config = config
    host = str(config.get("host") or "localhost")
    port = int(config.get("port") or 8765)
    server = ThreadingHTTPServer((host, port), GatewayHandler)
    print(f"unified_cli_gateway listening on http://{host}:{port}", flush=True)
    server.serve_forever()

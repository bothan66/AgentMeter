#!/usr/bin/env python3
"""Exercise a built proxy against a local fake upstream; no model API calls."""

import argparse
import json
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml


class Upstream(BaseHTTPRequestHandler):
    requests_seen = []

    def log_message(self, *_):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.requests_seen.append((self.path, body["model"]))
        assert self.headers["Authorization"] == "Bearer local-upstream-fixture"
        if body.get("stream"):
            events = [
                {
                    "id": "fixture",
                    "object": "chat.completion.chunk",
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": "OK"},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "fixture",
                    "object": "chat.completion.chunk",
                    "model": body["model"],
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
                },
            ]
            payload = (
                "".join("data: " + json.dumps(event) + "\n\n" for event in events)
                + "data: [DONE]\n\n"
            )
            mime = "text/event-stream"
        else:
            payload = json.dumps(
                {
                    "id": "fixture",
                    "object": "chat.completion",
                    "created": 1,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "OK"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
                }
            )
            mime = "application/json"
        encoded = payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve()
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="agentmeter-proxy-") as temporary:
        root = Path(temporary)
        config = {
            "host": "127.0.0.1",
            "port": port,
            "auth-dir": str(root / "auth"),
            "remote-management": {"disable-control-panel": True},
            "api-keys": ["local-client-fixture"],
            "openai-compatibility": [
                {
                    "name": "fixture",
                    "base-url": f"http://127.0.0.1:{upstream.server_port}/v1",
                    "api-key-entries": [{"api-key": "local-upstream-fixture"}],
                    "models": [{"name": "fixture-upstream", "alias": "Qwen3.6+"}],
                }
            ],
        }
        path = root / "config.yaml"
        path.write_text(yaml.safe_dump(config))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def request(endpoint, body=None, key="local-client-fixture"):
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/{endpoint}",
                data=json.dumps(body).encode() if body is not None else None,
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            )
            with opener.open(req, timeout=15) as response:
                return response.read().decode()

        with (root / "proxy.log").open("w+") as log:
            process = subprocess.Popen(
                [str(binary), "--config", str(path), "--local-model"],
                cwd=root,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Proxy exited before startup")
                    try:
                        models = json.loads(request("models"))
                        if any(m["id"] == "Qwen3.6+" for m in models["data"]):
                            break
                    except (urllib.error.URLError, TimeoutError):
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Proxy startup timed out")
                assert any(m["id"] == "Qwen3.6+" for m in models["data"])
                try:
                    request("models", key="wrong")
                except urllib.error.HTTPError as exc:
                    assert exc.code == 401
                else:
                    raise AssertionError("Proxy accepted an incorrect client key")
                prompts = {
                    "chat/completions": {"messages": [{"role": "user", "content": "Reply OK"}]},
                    "responses": {"input": [{"role": "user", "content": "Reply OK"}]},
                    "messages": {
                        "messages": [{"role": "user", "content": "Reply OK"}],
                        "max_tokens": 32,
                    },
                }
                for endpoint, prompt in prompts.items():
                    for stream in [False, True]:
                        response = request(endpoint, dict(prompt, model="Qwen3.6+", stream=stream))
                        assert "OK" in response, (endpoint, stream, response[:200])
                        print(f"PASS /v1/{endpoint} stream={stream}")
                assert len(Upstream.requests_seen) == 6
                assert all(
                    path == "/v1/chat/completions" and model == "fixture-upstream"
                    for path, model in Upstream.requests_seen
                )
                print("PASS authentication, model listing, alias mapping and six protocol routes")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                upstream.shutdown()


if __name__ == "__main__":
    main()

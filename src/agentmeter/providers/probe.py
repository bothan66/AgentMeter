#!/usr/bin/env python3
"""Minimal real Responses request using environment credentials; no Docker."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentmeter probe", description=__doc__)
    parser.parse_args(argv)
    key = os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    model = os.environ.get("AGENTMETER_MODEL")
    if not all((key, base, model)):
        print("Set OPENAI_API_KEY, OPENAI_BASE_URL and AGENTMETER_MODEL.", file=sys.stderr)
        return 2
    payload = {
        "model": model,
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": "Reply with OK only."}]}
        ],
        "max_output_tokens": 256,
    }
    request = urllib.request.Request(
        base + "/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
            status = response.status
    except urllib.error.HTTPError as exc:
        print(f"API request failed: HTTP {exc.code}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, ValueError):
        print(
            "API request failed: connection, timeout or response decoding error.", file=sys.stderr
        )
        return 1
    output = result.get("output", [])
    text = result.get("output_text") or "".join(
        part.get("text", "")
        for item in output
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )
    print(
        json.dumps(
            {
                "http_status": status,
                "status": result.get("status"),
                "has_output_text": bool(text),
                "usage": result.get("usage"),
            },
            indent=2,
        )
    )
    return 0 if result.get("status") == "completed" and text else 1


if __name__ == "__main__":
    raise SystemExit(main())

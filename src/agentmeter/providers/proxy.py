#!/usr/bin/env python3
"""Render a private CLIProxyAPI config from environment credentials."""

import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

import yaml


def build_config(args, env):
    required = [
        "AGENTMETER_PROXY_CLIENT_KEY",
        "UPSTREAM_OPENAI_API_KEY",
        "UPSTREAM_OPENAI_BASE_URL",
    ]
    if any(not env.get(name) for name in required):
        raise ValueError("Set " + ", ".join(required))
    upstream = env["UPSTREAM_OPENAI_BASE_URL"].rstrip("/")
    parsed = urlsplit(upstream)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError(
            "UPSTREAM_OPENAI_BASE_URL must be an HTTP(S) base URL without embedded credentials"
        )
    if not 1 <= args.port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    models = []
    seen = set()
    for mapping in args.model:
        alias, sep, name = mapping.partition("=")
        if not sep or not alias.strip() or not name.strip() or alias in seen:
            raise ValueError("Each --model must be a unique CLIENT_ALIAS=UPSTREAM_ID")
        seen.add(alias)
        models.append({"name": name, "alias": alias})
    return {
        "host": args.host,
        "port": args.port,
        "auth-dir": str(args.output.resolve().parent / "proxy-auth"),
        "logging-to-file": False,
        "remote-management": {
            "allow-remote": False,
            "secret-key": "",
            "disable-control-panel": True,
        },
        "api-keys": [env["AGENTMETER_PROXY_CLIENT_KEY"]],
        "openai-compatibility": [
            {
                "name": "agentmeter-provider",
                "base-url": upstream,
                "strip-unsupported-params": args.strip_unsupported_params,
                "inject-prompt-cache": args.inject_prompt_cache,
                "api-key-entries": [{"api-key": env["UPSTREAM_OPENAI_API_KEY"]}],
                "models": models,
            }
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentmeter proxy-config", description=__doc__)
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        help="CLIENT_ALIAS=UPSTREAM_ID; repeat for more models",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8317)
    parser.add_argument("--output", type=Path, default=Path("config.local.yaml"))
    parser.add_argument("--strip-unsupported-params", action="store_true")
    parser.add_argument("--inject-prompt-cache", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = build_config(args, os.environ)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(config, f, sort_keys=False)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Config not written: {exc}\n")
    print(
        f"Wrote {args.output}; {len(config['openai-compatibility'][0]['models'])} model aliases. Credentials are not printed."
    )


if __name__ == "__main__":
    main()

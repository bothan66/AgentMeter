import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_proxy_snapshot_matches_manifest():
    integration = ROOT / "integrations/cliproxyapi"
    manifest = json.loads((integration / "source-manifest.json").read_text())
    files = {
        p.relative_to(integration / "source").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (integration / "source").rglob("*")
        if p.is_file() and p.name != ".gitignore"
    }
    assert files == manifest["files"]
    canonical = "".join(f"{files[name]}  {name}\n" for name in sorted(files))
    assert hashlib.sha256(canonical.encode()).hexdigest() == manifest["snapshot_sha256"]


def test_private_config_renders_literal_credentials_and_refuses_overwrite(tmp_path):
    output = tmp_path / "config.local.yaml"
    env = dict(
        os.environ,
        AGENTMETER_PROXY_CLIENT_KEY="test-client-secret",
        UPSTREAM_OPENAI_API_KEY="test-upstream-secret",
        UPSTREAM_OPENAI_BASE_URL="http://127.0.0.1:19999/v1",
    )
    command = [
        sys.executable,
        "-m",
        "agentmeter",
        "proxy-config",
        "--model",
        "Qwen3.6+=provider/qwen",
        "--output",
        str(output),
    ]
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    config = yaml.safe_load(output.read_text())
    provider = config["openai-compatibility"][0]
    assert config["api-keys"] == ["test-client-secret"]
    assert provider["api-key-entries"] == [{"api-key": "test-upstream-secret"}]
    assert provider["models"] == [{"name": "provider/qwen", "alias": "Qwen3.6+"}]
    assert not provider["inject-prompt-cache"]
    assert not provider["strip-unsupported-params"]
    assert output.stat().st_mode & 0o777 == 0o600
    assert "test-client-secret" not in result.stdout + result.stderr
    assert "test-upstream-secret" not in result.stdout + result.stderr
    original = output.read_bytes()
    assert subprocess.run(command, env=env, capture_output=True).returncode != 0
    assert output.read_bytes() == original


def test_duplicate_route_is_rejected_before_creating_file(tmp_path):
    output = tmp_path / "config.local.yaml"
    env = dict(
        os.environ,
        AGENTMETER_PROXY_CLIENT_KEY="test-client",
        UPSTREAM_OPENAI_API_KEY="test-upstream",
        UPSTREAM_OPENAI_BASE_URL="http://127.0.0.1:19999/v1",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentmeter",
            "proxy-config",
            "--model",
            "same=one",
            "--model",
            "same=two",
            "--output",
            str(output),
        ],
        env=env,
        capture_output=True,
    )
    assert result.returncode != 0
    assert not output.exists()

"""Test setup against a tiny local Git upstream; no downloads or installs."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentmeter.runtime.setup import setup_runtime

pytestmark = pytest.mark.skipif(sys.version_info < (3, 12), reason="Harbor requires Python >= 3.12")


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def runtime_repo(tmp_path):
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git(upstream, "init", "--quiet")
    git(upstream, "config", "user.name", "Test")
    git(upstream, "config", "user.email", "test@example.invalid")
    (upstream / "runner.py").write_text("MODE = 'upstream'\n")
    git(upstream, "add", ".")
    git(upstream, "commit", "--quiet", "-m", "initial")
    commit = git(upstream, "rev-parse", "HEAD")
    repo = tmp_path / "agentmeter"
    (repo / "integrations").mkdir(parents=True)
    patch = repo / "integrations/adapter.patch"
    patch.write_text(
        "diff --git a/runner.py b/runner.py\n"
        "--- a/runner.py\n+++ b/runner.py\n@@ -1 +1 @@\n"
        "-MODE = 'upstream'\n+MODE = 'agentmeter'\n"
    )
    (repo / "integrations/agentmeter_runtime.lock.json").write_text(
        json.dumps(
            {
                "harbor": {
                    "repository": str(upstream),
                    "commit": commit,
                    "patches": ["integrations/adapter.patch"],
                },
            }
        )
    )
    return repo


def test_setup_is_pinned_and_idempotent(runtime_repo):
    checkout = setup_runtime(runtime_repo, install=False)
    assert (checkout / "runner.py").read_text() == "MODE = 'agentmeter'\n"
    expected = json.loads((runtime_repo / "integrations/agentmeter_runtime.lock.json").read_text())[
        "harbor"
    ]["commit"]
    assert git(checkout, "rev-parse", "HEAD") == expected
    assert setup_runtime(runtime_repo, install=False) == checkout
    assert sorted(p.name for p in checkout.parent.iterdir()) == ["harbor"]


@pytest.mark.parametrize("change", ["tracked", "untracked", "patch"])
def test_setup_preserves_unknown_changes(runtime_repo, change):
    checkout = setup_runtime(runtime_repo, install=False)
    if change == "tracked":
        edited = checkout / "runner.py"
        edited.write_text("MODE = 'user-edit'\n")
    elif change == "untracked":
        edited = checkout / "user-notes.txt"
        edited.write_text("keep this file")
    else:
        edited = runtime_repo / "integrations/adapter.patch"
        edited.write_text(edited.read_text().replace("agentmeter", "changed-adapter"))
    before = edited.read_bytes()
    with pytest.raises(ValueError, match="untracked files|differs from"):
        setup_runtime(runtime_repo, install=False)
    assert edited.read_bytes() == before


def test_setup_refuses_non_git_destination(runtime_repo):
    checkout = runtime_repo / "vendor/harbor"
    checkout.mkdir(parents=True)
    (checkout / "notes").write_text("user data")
    with pytest.raises(ValueError, match="non-Git path"):
        setup_runtime(runtime_repo, install=False)
    assert (checkout / "notes").read_text() == "user data"


@pytest.mark.parametrize(
    "python_packages",
    [None, {"litellm": "1.91.0", "claude-agent-sdk": "0.1.20"}],
)
def test_install_applies_optional_python_pins_in_one_pip_call(
    runtime_repo, monkeypatch, python_packages
):
    lock_path = runtime_repo / "integrations/agentmeter_runtime.lock.json"
    if python_packages is not None:
        lock = json.loads(lock_path.read_text())
        lock["python_packages"] = python_packages
        lock_path.write_text(json.dumps(lock))

    bin_dir = runtime_repo.parent / "test-bin"
    bin_dir.mkdir()
    python = str(bin_dir / "python")
    harbor = bin_dir / "harbor"
    harbor.touch()
    monkeypatch.setattr("agentmeter.runtime.setup.sys.executable", python)
    real_run = subprocess.run
    install_commands = []

    def fake_install(command, **kwargs):
        if command[0] in {python, str(harbor)}:
            install_commands.append(command)
            return subprocess.CompletedProcess(command, 0)
        return real_run(command, **kwargs)

    monkeypatch.setattr("agentmeter.runtime.setup.subprocess.run", fake_install)
    checkout = setup_runtime(runtime_repo)
    expected_requirements = [
        f"{name}=={version}" for name, version in (python_packages or {}).items()
    ]
    assert install_commands == [
        [python, "-m", "pip", "install", "-e", str(checkout), *expected_requirements],
        [str(harbor), "--help"],
    ]

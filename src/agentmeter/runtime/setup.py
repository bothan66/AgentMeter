"""Install the locked Harbor revision with AgentMeter's checked-in adapters."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _git(checkout: Path, *arguments: str, env: dict[str, str] | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _expected_diff(checkout: Path, commit: str, patches: list[Path]) -> bytes:
    """Compute patched content in an isolated index, without changing files."""
    with tempfile.TemporaryDirectory(prefix="agentmeter-index-", dir=checkout.parent) as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"))
        _git(checkout, "read-tree", commit, env=env)
        for patch in patches:
            _git(checkout, "apply", "--cached", str(patch), env=env)
        return _git(checkout, "diff", "--cached", "--binary", "--no-ext-diff", commit, env=env)


def setup_runtime(repo: Path, *, vendor_dir: Path | None = None, install: bool = True) -> Path:
    """Prepare Harbor, accepting only pristine or exactly AgentMeter-patched trees.

    The expected patch is rebuilt from today's lock and patch files on every
    invocation. A stale marker cannot authorize overwriting local changes.
    No benchmark task dataset is downloaded.
    """
    repo = Path(repo).resolve()
    if sys.version_info < (3, 12):
        raise ValueError("Harbor requires Python 3.12 or newer")
    if shutil.which("git") is None:
        raise ValueError("Git is required to install Harbor")
    lock = json.loads((repo / "integrations/agentmeter_runtime.lock.json").read_text())
    python_packages = lock.get("python_packages", {})
    if not isinstance(python_packages, dict):
        raise ValueError("Runtime python_packages must map package names to exact versions")
    python_requirements = []
    for package, version in python_packages.items():
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", package)
            or not isinstance(version, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", version)
        ):
            raise ValueError(f"Invalid Python package pin in runtime lock: {package}")
        python_requirements.append(f"{package}=={version}")
    config = lock["harbor"]
    commit = config["commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Harbor lock must specify a full 40-character Git commit")
    patches = [(repo / name).resolve() for name in config["patches"]]
    if not patches or any(not p.is_relative_to(repo) or not p.is_file() for p in patches):
        raise ValueError("Harbor patches must exist inside the AgentMeter repository")
    vendor = (
        Path(vendor_dir or os.environ.get("AGENTMETER_VENDOR_DIR", repo / "vendor"))
        .expanduser()
        .resolve()
    )
    checkout = vendor / "harbor"
    if checkout.exists() and not (checkout / ".git").exists():
        raise ValueError(f"Refusing to replace non-Git path: {checkout}")
    created = not checkout.exists()
    current = None
    dirty = False
    if created:
        checkout.mkdir(parents=True)
        _git(checkout, "init", "--quiet")
        _git(checkout, "remote", "add", "origin", config["repository"])
    else:
        # Reject untracked files independently: git diff does not include them.
        if _git(checkout, "ls-files", "--others", "--exclude-standard").strip():
            raise ValueError(
                f"Refusing to alter a Harbor checkout with untracked files: {checkout}"
            )
    try:
        _git(checkout, "cat-file", "-e", f"{commit}^{{commit}}")
    except subprocess.CalledProcessError:
        _git(checkout, "fetch", "--depth", "1", "--filter=blob:none", config["repository"], commit)
    if not created:
        current = _git(checkout, "rev-parse", "HEAD").decode().strip()
        dirty = bool(_git(checkout, "status", "--porcelain").strip())
        if current != commit and dirty:
            raise ValueError(
                f"Refusing to alter a dirty Harbor checkout at another revision: {checkout}"
            )
    if created or current != commit:
        _git(checkout, "checkout", "--detach", commit)
    expected = _expected_diff(checkout, commit, patches)
    actual = _git(checkout, "diff", "--binary", "--no-ext-diff", "HEAD")
    if (actual and actual != expected) or (dirty and not actual):
        raise ValueError(
            f"Harbor checkout differs from the locked AgentMeter patches: {checkout}; use a new --vendor-dir"
        )
    if not actual:
        # Validate the full combined patch before applying any of it.
        subprocess.run(
            ["git", "-C", str(checkout), "apply", "--check", "-"],
            input=expected,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "-C", str(checkout), "apply", "-"],
            input=expected,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    if install:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(checkout), *python_requirements],
            check=True,
        )
        harbor = Path(sys.executable).parent / "harbor"
        if not harbor.is_file():
            raise ValueError(f"Harbor installation did not provide {harbor}")
        subprocess.run([str(harbor), "--help"], check=True, stdout=subprocess.DEVNULL)
    return checkout

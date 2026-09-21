#!/usr/bin/env python3
"""Fail when tracked files contain common high-confidence credentials."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


PATTERNS = {
    "OpenAI-style API key": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(rb"\b(?:gh[opusr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(item.decode()) for item in output.split(b"\0") if item]


def main() -> int:
    paths = tracked_files()
    findings: list[tuple[Path, str]] = []
    for path in paths:
        try:
            data = path.read_bytes()
        except (FileNotFoundError, IsADirectoryError):
            continue
        if b"\0" in data[:8192]:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append((path, label))

    if findings:
        for path, label in findings:
            print(f"credential check failed: {path} ({label})")
        return 1
    print(f"PASS: scanned {len(paths)} tracked files; no high-confidence credentials found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

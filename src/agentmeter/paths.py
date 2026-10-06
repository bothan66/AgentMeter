"""Locate the research checkout without relying on an installed module's path."""

from __future__ import annotations

import os
from pathlib import Path


def find_repository(explicit: str | Path | None = None) -> Path:
    """Find the checkout that holds task bundles, result records, and patches.

    Installed Python code can run anywhere. Commands using research artifacts
    need a checkout, selected by argument, AGENTMETER_REPO_ROOT, or the current
    working directory. Editable installations also support source discovery.
    """
    configured = explicit or os.environ.get("AGENTMETER_REPO_ROOT")
    if configured:
        candidates = [Path(configured).expanduser().resolve()]
    else:
        candidates = []
        for start in (Path.cwd(), Path(__file__).resolve().parent):
            candidates.extend((start, *start.parents))

    for candidate in dict.fromkeys(candidates):
        if all(
            (candidate / name).exists()
            for name in (
                "pyproject.toml",
                "configs/task_lists",
                "artifacts/scoring",
                "integrations/agentmeter_runtime.lock.json",
            )
        ):
            return candidate
    raise FileNotFoundError(
        "AgentMeter research checkout not found. Run from the cloned repository "
        "or set AGENTMETER_REPO_ROOT to its path."
    )

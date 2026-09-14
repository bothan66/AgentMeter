from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any


def render_eval_command(template: str, task_dir: str | Path, run_dir: str | Path, task_id: str, model: str, cli: str, timeout_sec: int) -> str:
    return template.format(
        task_dir=Path(task_dir).resolve(),
        run_dir=Path(run_dir).resolve(),
        task_id=task_id,
        model=model,
        cli=cli,
        timeout_sec=timeout_sec,
    )


def run_eval_command(command: str, cwd: str | Path, timeout_sec: int) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=cwd, shell=True, text=True, capture_output=True, timeout=timeout_sec, check=False)
    return {
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "duration_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
        "error": None if completed.returncode == 0 else "evaluation failed",
    }

"""Check that released selections and description combinations are executable inputs."""

import csv
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_local_inputs_are_included():
    """Catch inputs present locally but omitted from a fresh Git checkout."""
    released = None
    if (ROOT / ".git").exists():
        names = (
            subprocess.check_output(
                ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                cwd=ROOT,
            )
            .decode()
            .split("\0")
        )
        released = {ROOT / name for name in names if name}
    for dockerfile in (ROOT / "benchmark_tasks").glob("*/*/environment/Dockerfile"):
        for line in dockerfile.read_text().splitlines():
            if not line.split() or line.split()[0].upper() not in {"COPY", "ADD"}:
                continue
            parts = shlex.split(line, comments=True)
            if any(part.startswith("--from=") for part in parts):
                continue
            sources = [part for part in parts[1:-1] if not part.startswith("--")]
            for source in sources:
                if source.startswith(("https://", "http://")):
                    continue
                matches = list(dockerfile.parent.glob(source))
                assert matches, (dockerfile, source)
                for path in matches:
                    assert path.exists(), (dockerfile, source)
                    if released is not None:
                        if path.is_file():
                            assert path in released, f"Unreleased Docker input: {path}"
                        else:
                            assert any(path in item.parents for item in released), path


def test_frozen_selections_and_descriptions():
    lists = ROOT / "configs/task_lists"
    selections = {}
    for filename, count in [
        ("full80.txt", 80),
        ("core30.public.txt", 30),
        ("agentmeter_opt_final16.txt", 16),
    ]:
        ids = (lists / filename).read_text().splitlines()
        assert len(ids) == len(set(ids)) == count
        selections[count] = set(ids)
    assert selections[30] <= selections[80]
    for task in selections[16]:
        matches = list((ROOT / "benchmark_tasks").glob(f"*/{task}"))
        assert len(matches) == 1, task
        task_dir = matches[0]
        for required in ["instruction.md", "task.toml", "environment/Dockerfile", "tests/test.sh"]:
            assert (task_dir / required).is_file(), (task, required)
    descriptions = list(
        (ROOT / "artifacts/agentmeter_opt_final16/descriptions").glob(
            "*/*/optimized_instruction.md"
        )
    )
    expected = {
        "qwen36_codex": {"regex-log", "citation-check", "sales-pivot-analysis"},
        "qwen36_kimi_cli": {"dm-csv-011", "bash-script-debugger"},
        "deepseek_v4_kimi_cli": {
            "dm-csv-009",
            "pddl-tpp-planning",
            "virtualhome-agent-planning",
            "lru-cache-with-ttl",
        },
        "glm51_qwen_coder": {"dm-csv-009", "bash-script-debugger", "sales-pivot-analysis"},
    }
    assert {(p.parent.parent.name, p.parent.name) for p in descriptions} == {
        (source, task) for source, tasks in expected.items() for task in tasks
    }
    assert len(descriptions) == 12
    assert len({p.parent.name for p in descriptions}) == 9
    for optimized in descriptions:
        (task_dir,) = (ROOT / "benchmark_tasks").glob(f"*/{optimized.parent.name}")
        assert (
            optimized.with_name("baseline_instruction.md").read_bytes()
            == (task_dir / "instruction.md").read_bytes()
        )
        assert optimized.stat().st_size > 0


def test_cross_grid_is_complete_and_unique():
    with (ROOT / "artifacts/agentmeter_opt_final16/results/cross_task_results.csv").open() as f:
        rows = list(csv.DictReader(f))
    keys = [(r["task_id"], r["source_combo"], r["target_combo"]) for r in rows]
    assert len(keys) == len(set(keys)) == 192
    assert all(source != target for _, source, target in keys)

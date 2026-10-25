"""Check benchmark task selections, description pairs, and Docker build dependencies."""

import json
import shlex
import subprocess
from pathlib import Path

from agentmeter.runtime.skills import load_skill_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_source_licenses_and_skill_revision_are_recorded():
    for family, license_name in (
        ("skillsbench", "Apache License"),
        ("terminal_bench", "Apache License"),
        ("da_code", "MIT License"),
    ):
        assert license_name in (ROOT / "benchmark_tasks" / family / "LICENSE").read_text()
    manifest = json.loads((ROOT / "integrations/skillsbench/skills_manifest.json").read_text())
    lock = json.loads((ROOT / "integrations/agentmeter_runtime.lock.json").read_text())
    assert manifest["upstream_commit"] == lock["skillsbench"]["commit"]
    assert len(manifest["upstream_commit"]) == 40


def test_dockerfile_local_inputs_are_included():
    """Require local build inputs or an explicit external skill dependency."""
    external_skills = load_skill_manifest(ROOT)
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
                task_dir = dockerfile.parent.parent
                if (
                    source == "skills"
                    and task_dir.parent.name == "skillsbench"
                    and task_dir.name in external_skills
                ):
                    assert external_skills[task_dir.name]
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
    sources = {
        "qwen36_codex",
        "qwen36_kimi_cli",
        "deepseek_v4_kimi_cli",
        "glm51_qwen_coder",
    }
    tasks = {
        "dm-csv-009",
        "citation-check",
        "csv-data-validator",
        "econ-detrending-correlation",
    }
    assert {(p.parent.parent.name, p.parent.name) for p in descriptions} == {
        (source, task) for source in sources for task in tasks
    }
    assert len(descriptions) == 16
    for optimized in descriptions:
        (task_dir,) = (ROOT / "benchmark_tasks").glob(f"*/{optimized.parent.name}")
        assert (
            optimized.with_name("baseline_instruction.md").read_bytes()
            == (task_dir / "instruction.md").read_bytes()
        )
        assert optimized.stat().st_size > 0

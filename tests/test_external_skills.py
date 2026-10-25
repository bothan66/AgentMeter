"""External dependencies stay reproducible without bundling skill contents."""

import hashlib
import json
from pathlib import Path

import pytest

from agentmeter.runtime import RunOptions, plan_suite, run_plan
from agentmeter.runtime.skills import (
    MANIFEST_PATH,
    load_skill_manifest,
    prepare_skills,
    verify_task_skills,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def skill_checkout(tmp_path):
    repo, source = tmp_path / "release", tmp_path / "upstream/tasks"
    files = {"sample/SKILL.md": b"Skill fixture\n", "sample/reference.txt": b"Reference\n"}
    manifest = repo / MANIFEST_PATH
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "executable_files": {"example": ["sample/reference.txt"]},
                "tasks": {
                    "example": {
                        name: hashlib.sha256(content).hexdigest() for name, content in files.items()
                    }
                },
            }
        )
    )
    for name, content in files.items():
        path = source / "example/environment/skills" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return repo, source


def test_inventory_covers_seven_tasks_and_nine_skill_directories():
    tasks = load_skill_manifest(ROOT)
    assert len(tasks) == 7
    assert sum(len(files) for files in tasks.values()) == 33
    assert sum(name.endswith("/SKILL.md") for files in tasks.values() for name in files) == 9
    for task in tasks:
        assert (ROOT / "benchmark_tasks/skillsbench" / task / "environment/Dockerfile").is_file()


def test_prepare_verifies_and_is_idempotent(skill_checkout):
    repo, source = skill_checkout
    assert prepare_skills(repo, source, ["example"]) == 2
    assert prepare_skills(repo, source) == 0
    task = repo / "benchmark_tasks/skillsbench/example"
    verify_task_skills(task)
    assert (task / "environment/skills/sample/reference.txt").read_bytes() == b"Reference\n"
    assert (task / "environment/skills/sample/reference.txt").stat().st_mode & 0o111 == 0o111


@pytest.mark.parametrize("failure", ["missing", "changed"])
def test_invalid_source_creates_no_partial_dependency_tree(skill_checkout, failure):
    repo, source = skill_checkout
    reference = source / "example/environment/skills/sample/reference.txt"
    if failure == "missing":
        reference.unlink()
    else:
        reference.write_text("Different upstream version")
    with pytest.raises(ValueError):
        prepare_skills(repo, source)
    assert not (repo / "benchmark_tasks").exists()


def test_existing_changed_files_are_not_overwritten(skill_checkout):
    repo, source = skill_checkout
    prepare_skills(repo, source)
    path = repo / "benchmark_tasks/skillsbench/example/environment/skills/sample/SKILL.md"
    path.write_text("User edits")
    with pytest.raises(ValueError, match="differs"):
        prepare_skills(repo, source)
    assert path.read_text() == "User edits"
    with pytest.raises(ValueError, match="prepare-skills"):
        verify_task_skills(path.parents[3])


def test_missing_skills_fail_before_harbor_or_job_creation(skill_checkout, tmp_path):
    repo, _ = skill_checkout
    task = repo / "benchmark_tasks/skillsbench/example"
    (task / "tests").mkdir(parents=True)
    for name in ("instruction.md", "task.toml", "tests/test.sh"):
        (task / name).write_text("fixture")
    task_list = tmp_path / "tasks.txt"
    task_list.write_text("example\n")
    jobs = tmp_path / "jobs"
    plan = plan_suite(
        repo,
        task_list,
        repo / "benchmark_tasks",
        RunOptions("model", "codex", "/bin/true"),
        jobs_dir=jobs,
    )
    with pytest.raises(ValueError, match="prepare-skills"):
        run_plan(plan)
    assert not jobs.exists()


def test_symlinks_cannot_escape_dependency_tree(skill_checkout, tmp_path):
    repo, source = skill_checkout
    original = source / "example/environment/skills/sample/SKILL.md"
    external = tmp_path / "external.md"
    external.write_bytes(original.read_bytes())
    original.unlink()
    original.symlink_to(external)
    with pytest.raises(ValueError, match="symlink"):
        prepare_skills(repo, source)
    assert not (repo / "benchmark_tasks").exists()


def test_unknown_task_is_rejected(skill_checkout):
    repo, source = skill_checkout
    with pytest.raises(ValueError, match="No external skills"):
        prepare_skills(repo, source, ["unknown"])
    assert not (repo / "benchmark_tasks").exists()


def test_other_task_collections_are_not_subject_to_release_manifest(tmp_path):
    verify_task_skills(tmp_path / "external/tasks/example")

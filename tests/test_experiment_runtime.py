"""Experiment planning and Harbor launch contracts without model or Docker calls."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agentmeter.runtime import RunOptions, plan_comparison, plan_suite, run_plan

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = RunOptions("provider/model", "codex", "/bin/true", "0.153.0")


def cli_environment(**overrides):
    return dict(os.environ, PYTHONPATH=str(ROOT / "src"), **overrides)


def test_unreleased_description_fails_before_execution(tmp_path):
    with pytest.raises(ValueError, match="not included in this example release"):
        plan_comparison(
            ROOT,
            "qwen36_codex",
            "optimized",
            ["lru-cache-with-ttl"],
            OPTIONS,
            jobs_dir=tmp_path / "jobs",
        )
    assert not (tmp_path / "jobs").exists()


def test_comparison_preserves_snapshot_and_refuses_overwrite(tmp_path, monkeypatch):
    jobs = tmp_path / "jobs with spaces"
    plan = plan_comparison(
        ROOT, "qwen36_codex", "optimized", ["dm-csv-009"], OPTIONS, jobs_dir=jobs
    )
    calls = []

    def mock_harbor(command, *, check):
        assert check
        path = Path(command[command.index("-p") + 1])
        assert (path / "instruction.md").read_bytes() == plan.tasks[0].instruction.read_bytes()
        calls.append(command)

    monkeypatch.setattr("agentmeter.runtime.experiments.subprocess.run", mock_harbor)
    run_plan(plan)
    assert calls == [
        [
            "/bin/true",
            "run",
            "-p",
            str(jobs / "task_snapshots/dm-csv-009"),
            "-a",
            "codex",
            "-m",
            "provider/model",
            "--ak",
            "version=0.153.0",
            "-e",
            "docker",
            "-k",
            "1",
            "-n",
            "1",
            "--job-name",
            "final16_dm-csv-009_qwen36_codex_optimized",
            "--jobs-dir",
            str(jobs),
        ]
    ]
    with pytest.raises(ValueError, match="snapshot already exists"):
        run_plan(plan)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "source", ["qwen36_codex", "qwen36_kimi_cli", "deepseek_v4_kimi_cli", "glm51_qwen_coder"]
)
def test_default_conditions_use_same_released_tasks(tmp_path, source):
    plans = [
        plan_comparison(ROOT, source, variant, [], OPTIONS, jobs_dir=tmp_path / variant)
        for variant in ("original", "optimized")
    ]
    selected = [{task.task_id for task in plan.tasks} for plan in plans]
    descriptions = ROOT / "artifacts/agentmeter_opt_final16/descriptions" / source
    assert (
        selected[0]
        == selected[1]
        == {p.parent.name for p in descriptions.glob("*/optimized_instruction.md")}
    )
    for task in plans[0].tasks:
        assert task.instruction == task.source / "instruction.md"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("tail", ["not-a-released-task", "regex-log", "../regex-log"])
def test_invalid_batch_creates_no_partial_run(tmp_path, tail):
    jobs = tmp_path / "jobs"
    with pytest.raises(ValueError):
        plan_comparison(
            ROOT, "qwen36_codex", "original", ["regex-log", tail], OPTIONS, jobs_dir=jobs
        )
    assert not jobs.exists()


def test_suite_preflight_and_final_line_without_newline(tmp_path):
    task_list, jobs = tmp_path / "tasks.txt", tmp_path / "jobs"
    for content in ("regex-log\nmissing-task", "regex-log\nregex-log", ""):
        task_list.write_text(content)
        with pytest.raises(ValueError):
            plan_suite(ROOT, task_list, ROOT / "benchmark_tasks", OPTIONS, jobs_dir=jobs)
        assert not jobs.exists()
    task_list.write_text("# selected tasks\r\n\r\nregex-log")
    plan = plan_suite(ROOT, task_list, ROOT / "benchmark_tasks", OPTIONS, jobs_dir=jobs)
    run_plan(plan)
    assert jobs.is_dir()
    assert plan.tasks[0].execution_path == ROOT / "benchmark_tasks/terminal_bench/regex-log"


def test_suite_rejects_ambiguous_task(tmp_path):
    for family in ("one", "two"):
        task = tmp_path / family / "same-task"
        task.mkdir(parents=True)
        (task / "instruction.md").write_text("test")
    task_list = tmp_path / "tasks.txt"
    task_list.write_text("same-task")
    with pytest.raises(ValueError, match="found 2"):
        plan_suite(ROOT, task_list, tmp_path, OPTIONS)


def test_existing_suite_job_is_never_overwritten(tmp_path):
    task_list, jobs = tmp_path / "tasks.txt", tmp_path / "jobs"
    task_list.write_text("regex-log")
    plan = plan_suite(ROOT, task_list, ROOT / "benchmark_tasks", OPTIONS, jobs_dir=jobs)
    existing = jobs / plan.tasks[0].job_name
    existing.mkdir(parents=True)
    (existing / "result.json").write_text('{"prior_run": true}')
    with pytest.raises(ValueError, match="job already exists"):
        run_plan(plan)
    with pytest.raises(ValueError, match="job already exists"):
        plan_suite(ROOT, task_list, ROOT / "benchmark_tasks", OPTIONS, jobs_dir=jobs)
    assert (existing / "result.json").read_text() == '{"prior_run": true}'


def test_incomplete_comparison_environment_fails_before_any_snapshot(tmp_path):
    task = tmp_path / "benchmark_tasks/terminal_bench/incomplete"
    task.mkdir(parents=True)
    (task / "instruction.md").write_text("task")
    (task / "task.toml").write_text("version = '1.0'")
    with pytest.raises(ValueError, match="Incomplete task"):
        plan_comparison(tmp_path, "qwen36_codex", "original", ["incomplete"], OPTIONS)
    assert not (tmp_path / "jobs").exists()


def test_environment_settings_are_overridable_without_recording_credentials():
    settings = RunOptions.from_environment(
        model="explicit",
        environment={
            "AGENTMETER_MODEL": "fallback",
            "AGENTMETER_AGENT": "codex",
            "AGENTMETER_HARBOR_BIN": "/bin/true",
            "AGENTMETER_AGENT_VERSION": "0.153.0",
            "OPENAI_API_KEY": "test-provider-key",
        },
    )
    assert settings == RunOptions("explicit", "codex", "/bin/true", "0.153.0")
    assert "test-provider-key" not in repr(settings)


@pytest.mark.parametrize("multiplier", [0, -1, float("nan"), float("inf"), -float("inf")])
def test_setup_timeout_multiplier_rejects_invalid_values(multiplier):
    with pytest.raises(ValueError, match="positive finite"):
        RunOptions("model", "codex", setup_timeout_multiplier=multiplier)


def test_setup_timeout_multiplier_does_not_change_execution_budgets(tmp_path):
    options = RunOptions.from_environment(
        model="model",
        agent="codex",
        setup_timeout_multiplier=3.0,
    )
    plan = plan_comparison(
        ROOT, "qwen36_codex", "original", ["regex-log"], options, jobs_dir=tmp_path / "jobs"
    )
    command = plan.command(plan.tasks[0])
    assert command[command.index("--agent-setup-timeout-multiplier") + 1] == "3.0"
    assert "--timeout-multiplier" not in command
    assert "--agent-timeout-multiplier" not in command
    assert "--verifier-timeout-multiplier" not in command


@pytest.mark.parametrize("errors", [0, 1])
def test_harbor_trial_errors_are_distinct_from_zero_reward(tmp_path, monkeypatch, errors):
    plan = plan_comparison(
        ROOT, "qwen36_codex", "original", ["regex-log"], OPTIONS, jobs_dir=tmp_path / "jobs"
    )

    def mock_harbor(command, *, check):
        result_path = plan.jobs_dir / plan.tasks[0].job_name / "result.json"
        result_path.parent.mkdir(parents=True)
        result_path.write_text(
            json.dumps(
                {
                    "stats": {"n_errors": errors, "evals": {"reward": 0}},
                }
            )
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("agentmeter.runtime.experiments.subprocess.run", mock_harbor)
    if errors:
        with pytest.raises(ValueError, match="Harbor reported 1 trial error.*result.json"):
            run_plan(plan)
    else:
        run_plan(plan)


def test_cli_dry_run_does_not_create_jobs_or_require_harbor(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentmeter",
            "compare",
            "qwen36_codex",
            "optimized",
            "dm-csv-009",
            "--model",
            "model",
            "--agent",
            "codex",
            "--jobs-dir",
            str(tmp_path / "jobs"),
            "--harbor",
            "/definitely/uninstalled/harbor",
            "--setup-timeout-multiplier",
            "3",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        env=cli_environment(),
    )
    assert result.returncode == 0, result.stderr
    assert "--job-name final16_dm-csv-009_qwen36_codex_optimized" in result.stdout
    assert "optimized_instruction.md" in result.stdout
    assert "--agent-setup-timeout-multiplier 3.0" in result.stdout
    assert not (tmp_path / "jobs").exists()


def test_cli_forwards_provider_environment_to_mock_harbor(tmp_path):
    mock_harbor = tmp_path / "mock-harbor"
    capture = tmp_path / "capture.json"
    mock_harbor.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys\n"
        "pathlib.Path(os.environ['MOCK_CAPTURE']).write_text(json.dumps({"
        "'args': sys.argv[1:], 'key_present': os.environ.get('OPENAI_API_KEY') == 'fixture-key',"
        "'base_url': os.environ.get('OPENAI_BASE_URL')}))\n"
    )
    mock_harbor.chmod(0o700)
    env = cli_environment(
        OPENAI_API_KEY="fixture-key",
        OPENAI_BASE_URL="http://fixture.invalid/v1",
        MOCK_CAPTURE=str(capture),
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentmeter",
            "compare",
            "qwen36_codex",
            "original",
            "regex-log",
            "--model",
            "test-model",
            "--agent",
            "codex",
            "--jobs-dir",
            str(tmp_path / "jobs"),
            "--harbor",
            str(mock_harbor),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(capture.read_text())
    assert payload["key_present"] and payload["base_url"] == "http://fixture.invalid/v1"
    assert payload["args"][0] == "run"
    assert "fixture-key" not in result.stdout + result.stderr

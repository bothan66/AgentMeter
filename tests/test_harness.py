import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from agentmeter.harness import (
    ApiConfig,
    Experiment,
    Recorder,
    http_request,
    load_api_configs,
    load_manifest,
    normalize_api_response,
    read_yaml,
    run_api,
    run_experiment,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fake_runner(monkeypatch):
    """Use a fixed transport response only inside orchestration tests."""
    requests = []

    def respond(cfg, url, payload):
        requests.append((cfg, url, payload))
        return {
            "status": "completed",
            "stdout": "fixture runner completed\n",
            "summary": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        }

    monkeypatch.setattr("agentmeter.harness.http_request", respond)
    return requests


def test_api_runs_full_matrix_with_test_transport(tmp_path: Path, fake_runner):
    exp = Experiment.from_yaml(ROOT / "tests/fixtures/smoke.yaml")
    summaries = run_experiment(
        exp,
        task_root=ROOT / "tests/fixtures/toy_tasks",
        out=tmp_path / "runs",
        runner_config=ROOT / "tests/fixtures/runners.yaml",
        resume=False,
        force=True,
    )
    assert len(summaries) == 8
    assert len(fake_runner) == 8
    assert all(row["passed"] for row in summaries)


def test_real_api_key_header_not_recorded(tmp_path: Path, monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "status": "completed",
                    "stdout": "ok\n",
                    "summary": {
                        "passed": True,
                        "input_tokens": 1,
                        "output_tokens": 2,
                        "cache_read_tokens": 0,
                        "total_tokens": 3,
                        "exit_code": 0,
                    },
                }
            ).encode("utf-8")

    seen = {}

    def fake_urlopen(request, timeout):  # noqa: ARG001
        seen.update(dict(request.header_items()))
        return Response()

    cfg = tmp_path / "runners.local.yaml"
    cfg.write_text(
        "api_runners:\n"
        "  cli_a_mock:\n"
        '    url: "https://example.invalid/run"\n'
        "    method: POST\n"
        "    api_key_env: AGENTMETER_TEST_KEY\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTMETER_TEST_KEY", "real-key-placeholder")
    exp = Experiment.from_yaml(ROOT / "tests/fixtures/smoke.yaml")
    exp = exp.__class__(**{**exp.__dict__, "models": ("model_a_mock",), "clis": ("cli_a_mock",)})
    with patch("urllib.request.urlopen", fake_urlopen):
        run_experiment(
            exp,
            task_root=ROOT / "tests/fixtures/toy_tasks",
            out=tmp_path / "runs",
            runner_config=cfg,
            resume=False,
            force=True,
            task_ids={"toy_bugfix_001"},
        )
    assert seen["Authorization"] == "Bearer real-key-placeholder"
    text_suffixes = {".json", ".jsonl", ".txt", ".diff", ".csv", ".md", ".py", ".sh"}
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (tmp_path / "runs").rglob("*")
        if path.is_file() and path.suffix in text_suffixes
    )
    assert "real-key-placeholder" not in combined


def test_unified_response_formats_are_normalized():
    anthropic = normalize_api_response(
        {
            "content": [{"type": "text", "text": "done"}],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 2,
                "cache_creation_input_tokens": 3,
                "cache_read_input_tokens": 1,
            },
        },
        ApiConfig(url="https://runner.example.invalid", response_format="anthropic"),
    )
    assert anthropic["summary"]["total_tokens"] == 16
    assert anthropic["summary"]["cache_creation_tokens"] == 3
    assert anthropic["summary"]["cache_hit_tokens"] == 1
    assert anthropic["stdout"] == "done"

    responses = normalize_api_response(
        {
            "output_text": "done",
            "usage": {
                "input_tokens": 11,
                "output_tokens": 3,
                "total_tokens": 14,
                "input_token_details": {"cached_tokens": 4},
            },
        },
        ApiConfig(url="https://runner.example.invalid", response_format="responses"),
    )
    assert responses["summary"]["input_tokens"] == 11
    assert responses["summary"]["cache_hit_tokens"] == 4

    completions = normalize_api_response(
        {
            "choices": [{"message": {"content": "done"}}],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 4,
                "total_tokens": 16,
                "prompt_tokens_details": {"cached_tokens": 5},
            },
        },
        ApiConfig(url="https://runner.example.invalid", response_format="completions"),
    )
    assert completions["summary"]["output_tokens"] == 4
    assert completions["summary"]["cache_hit_tokens"] == 5


def test_missing_runner_configuration_fails_without_recursion(tmp_path):
    with pytest.raises(ValueError, match="runner configuration is required"):
        load_api_configs(None)
    with pytest.raises(FileNotFoundError, match="Runner configuration not found"):
        load_api_configs(tmp_path / "missing.yaml")


def test_responses_reports_standard_cached_input_tokens():
    response = normalize_api_response(
        {
            "output_text": "done",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "input_tokens_details": {"cached_tokens": 80},
            },
        },
        ApiConfig(url="https://runner.example.invalid", response_format="responses"),
    )
    assert response["summary"]["cache_hit_tokens"] == 80
    assert response["summary"]["total_tokens"] == 120


def test_runner_yaml_preserves_quoted_hash_and_multiline_payload(tmp_path):
    config = tmp_path / "runners.yaml"
    config.write_text(
        "api_runners:\n"
        "  default:\n"
        "    url: 'https://example.invalid/v1#fragment'\n"
        "    payload:\n"
        "      instruction: |\n"
        "        Write a file.\n"
        "        Keep the # marker.\n",
        encoding="utf-8",
    )
    data = read_yaml(config)
    assert data["api_runners"]["default"]["url"].endswith("#fragment")
    assert (
        data["api_runners"]["default"]["payload"]["instruction"]
        == "Write a file.\nKeep the # marker.\n"
    )


def test_poll_requests_preserve_authentication(tmp_path, monkeypatch):
    exp = Experiment.from_yaml(ROOT / "tests/fixtures/smoke.yaml")
    task = load_manifest(exp.manifest)[0]
    cfg = ApiConfig(
        url="https://example.invalid/run",
        api_key_env="AGENTMETER_TEST_KEY",
        auth_header="X-API-Key",
        auth_scheme="",
        poll_interval_sec=0,
    )
    responses = iter(
        [
            {"status": "queued", "poll_url": "https://example.invalid/poll/123"},
            {"status": "completed", "stdout": "done"},
        ]
    )
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(next(responses)).encode("utf-8")

    def urlopen(request, timeout):
        requests.append(request)
        return Response()

    monkeypatch.setenv("AGENTMETER_TEST_KEY", "polling-key-placeholder")
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    response = run_api(
        cfg, task, "model", "cli", tmp_path, tmp_path, 60, Recorder(tmp_path / "events.jsonl")
    )
    assert response["status"] == "completed"
    assert [request.method for request in requests] == ["POST", "GET"]
    assert all(request.get_header("X-api-key") == "polling-key-placeholder" for request in requests)


def test_disabled_recording_options_do_not_create_output_files(tmp_path, fake_runner):
    exp = replace(
        Experiment.from_yaml(ROOT / "tests/fixtures/smoke.yaml"),
        models=("model_a_mock",),
        clis=("cli_a_mock",),
        record_trajectory=False,
        save_stdout=False,
        save_stderr=False,
        save_patch=False,
    )
    summaries = run_experiment(
        exp,
        task_root=ROOT / "tests/fixtures/toy_tasks",
        out=tmp_path / "runs",
        runner_config=ROOT / "tests/fixtures/runners.yaml",
        resume=False,
        force=True,
        task_ids={"toy_bugfix_001"},
    )
    run_dir = Path(summaries[0]["run_dir"])
    assert len(fake_runner) == 1
    assert (run_dir / "usage.json").is_file()
    for name in (
        "stdout.txt",
        "stderr.txt",
        "patch.diff",
        "trajectory.jsonl",
        "normalized_usage.json",
    ):
        assert not (run_dir / name).exists()


@pytest.mark.parametrize(
    "url",
    ["mock://local", "file:///tmp/result.json", "ftp://example.invalid", "https:///missing-host"],
)
def test_runner_rejects_non_http_urls_before_transport(url, monkeypatch):
    def unexpected_network(*args, **kwargs):
        pytest.fail("invalid runner URL must fail before issuing a request")

    monkeypatch.setattr("urllib.request.urlopen", unexpected_network)
    with pytest.raises(ValueError, match="Runner URL must use HTTP or HTTPS"):
        http_request(ApiConfig(url=url), url, {})

from pathlib import Path
from unittest.mock import patch
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from harness_lib import ApiConfig, Experiment, normalize_api_response, run_experiment


ROOT = Path(__file__).resolve().parents[1]


def test_mock_api_runs_full_matrix(tmp_path: Path):
    exp = Experiment.from_yaml(ROOT / "configs/experiments/smoke.example.yaml")
    summaries = run_experiment(
        exp,
        task_root=ROOT / "examples/toy_tasks",
        out=tmp_path / "runs",
        runner_config=ROOT / "configs/runners.example.yaml",
        resume=False,
        force=True,
    )
    assert len(summaries) == 8
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
                    "summary": {"passed": True, "input_tokens": 1, "output_tokens": 2, "cache_read_tokens": 0, "total_tokens": 3, "exit_code": 0},
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
        "    url: \"https://example.invalid/run\"\n"
        "    method: POST\n"
        "    api_key_env: AGENTMETER_TEST_KEY\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTMETER_TEST_KEY", "real-key-placeholder")
    exp = Experiment.from_yaml(ROOT / "configs/experiments/smoke.example.yaml")
    exp = exp.__class__(**{**exp.__dict__, "models": ("model_a_mock",), "clis": ("cli_a_mock",)})
    with patch("urllib.request.urlopen", fake_urlopen):
        run_experiment(
            exp,
            task_root=ROOT / "examples/toy_tasks",
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
            "usage": {"input_tokens": 10, "output_tokens": 2, "cache_creation_input_tokens": 3, "cache_read_input_tokens": 1},
        },
        ApiConfig(url="mock://local", response_format="anthropic"),
    )
    assert anthropic["summary"]["total_tokens"] == 16
    assert anthropic["summary"]["cache_creation_tokens"] == 3
    assert anthropic["summary"]["cache_hit_tokens"] == 1
    assert anthropic["stdout"] == "done"

    responses = normalize_api_response(
        {"output_text": "done", "usage": {"input_tokens": 11, "output_tokens": 3, "total_tokens": 14, "input_token_details": {"cached_tokens": 4}}},
        ApiConfig(url="mock://local", response_format="responses"),
    )
    assert responses["summary"]["input_tokens"] == 11
    assert responses["summary"]["cache_hit_tokens"] == 4

    completions = normalize_api_response(
        {
            "choices": [{"message": {"content": "done"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16, "prompt_tokens_details": {"cached_tokens": 5}},
        },
        ApiConfig(url="mock://local", response_format="completions"),
    )
    assert completions["summary"]["output_tokens"] == 4
    assert completions["summary"]["cache_hit_tokens"] == 5

"""The public Python entry point works without importing checkout-only scripts."""

import json

import pytest

from agentmeter.cli import main
from agentmeter.paths import find_repository


def test_score_works_outside_checkout_with_explicit_inputs(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs.csv"
    runs.write_text("task_id,stratum,reward,cost_usd\na,Easy,1,1\nb,Medium,1,1\nc,Hard,1,1\n")
    calibration = tmp_path / "calibration.json"
    calibration.write_text(
        json.dumps(
            {
                "alpha": 0.6,
                "currency": "USD",
                "strata": {
                    stratum: {"budgets_usd": [1, 2], "zero_reward_threshold_usd": 2}
                    for stratum in ("Easy", "Medium", "Hard")
                },
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    assert main(["score", "--runs", str(runs), "--calibration", str(calibration)]) == 0
    assert json.loads(capsys.readouterr().out)["AMS"] == pytest.approx(1.0)


def test_tables_use_explicit_checkout_from_another_directory(tmp_path, monkeypatch, capsys):
    checkout = find_repository()
    monkeypatch.chdir(tmp_path)
    assert main(["tables", "--repository", str(checkout), "--examples"]) == 0
    table = capsys.readouterr().out
    assert len(table.strip().splitlines()) == 6
    assert "dm-csv-009 / qwen36_codex" in table


def test_bad_explicit_checkout_does_not_fall_back(tmp_path, capsys):
    assert main(["tables", "--repository", str(tmp_path)]) == 1
    assert "checkout not found" in capsys.readouterr().err


def test_manifest_requires_a_checker_instead_of_running_an_oracle(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(
            [
                "manifest",
                "--task-root",
                str(tmp_path),
                "--suite",
                "custom",
                "--out",
                str(tmp_path / "manifest.csv"),
            ]
        )
    assert error.value.code == 2
    assert "--eval-command" in capsys.readouterr().err
    assert not (tmp_path / "manifest.csv").exists()


def test_help_does_not_require_optional_dependencies_or_credentials(monkeypatch, capsys):
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AGENTMETER_MODEL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert all(command in help_text for command in ("tables", "score", "optimize", "compare"))

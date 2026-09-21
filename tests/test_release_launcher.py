import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_unreleased_description_fails_before_execution():
    result = subprocess.run(
        ['bash', str(ROOT / 'scripts/run_final16_condition.sh'),
         'qwen36_codex', 'optimized', 'xlsx-recover-data'],
        capture_output=True, text=True,
    )
    assert result.returncode == 3
    assert 'not included in this example release' in result.stderr


def test_final16_preserves_snapshot_and_refuses_overwrite(tmp_path):
    # /bin/true substitutes only for Harbor; no network or paid model call.
    jobs = tmp_path / 'jobs with spaces'
    env = dict(os.environ, AGENTMETER_MODEL='provider/model',
               AGENTMETER_AGENT='codex', AGENTMETER_HARBOR_BIN='/bin/true',
               AGENTMETER_JOBS_DIR=str(jobs), AGENTMETER_AGENT_VERSION='0.153.0')
    cmd = ['bash', str(ROOT / 'scripts/run_final16_condition.sh'),
           'qwen36_codex', 'optimized', 'regex-log']
    subprocess.run(cmd, env=env, check=True, capture_output=True)
    snapshot = jobs / 'task_snapshots/regex-log/instruction.md'
    expected = ROOT / 'artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/regex-log/optimized_instruction.md'
    assert snapshot.read_bytes() == expected.read_bytes()
    rerun = subprocess.run(cmd, env=env, capture_output=True)
    assert rerun.returncode == 3
    assert snapshot.read_bytes() == expected.read_bytes()


def test_default_conditions_use_same_released_tasks(tmp_path):
    selected = []
    for variant in ['original', 'optimized']:
        jobs = tmp_path / variant
        env = dict(os.environ, AGENTMETER_MODEL='test', AGENTMETER_AGENT='codex',
                   AGENTMETER_HARBOR_BIN='/bin/true', AGENTMETER_JOBS_DIR=str(jobs))
        subprocess.run(['bash', str(ROOT / 'scripts/run_final16_condition.sh'),
                        'qwen36_codex', variant], env=env, check=True, capture_output=True)
        selected.append({p.name for p in (jobs / 'task_snapshots').iterdir()})
    expected = {p.name for p in (ROOT / 'artifacts/agentmeter_opt_final16/descriptions/qwen36_codex').iterdir() if p.is_dir()}
    assert selected[0] == selected[1] == expected


def test_invalid_batch_creates_no_partial_run(tmp_path):
    for tail in ['not-a-released-task', 'regex-log']:
        jobs = tmp_path / tail
        env = dict(os.environ, AGENTMETER_MODEL='test', AGENTMETER_AGENT='codex',
                   AGENTMETER_HARBOR_BIN='/bin/true', AGENTMETER_JOBS_DIR=str(jobs))
        result = subprocess.run(['bash', str(ROOT / 'scripts/run_final16_condition.sh'),
                                 'qwen36_codex', 'original', 'regex-log', tail],
                                env=env, capture_output=True)
        assert result.returncode == 3
        assert not jobs.exists()

"""Check that released selections and description combinations are executable inputs."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_selections_and_descriptions():
    lists = ROOT / 'configs/task_lists'
    selections = {}
    for filename, count in [('full80.txt', 80), ('core30.public.txt', 30), ('agentmeter_opt_final16.txt', 16)]:
        ids = (lists / filename).read_text().splitlines()
        assert len(ids) == len(set(ids)) == count
        selections[count] = set(ids)
    assert selections[30] <= selections[80]
    for task in selections[16]:
        matches = list((ROOT / 'benchmark_tasks').glob(f'*/{task}'))
        assert len(matches) == 1, task
        task_dir = matches[0]
        for required in ['instruction.md', 'task.toml', 'environment/Dockerfile', 'tests/test.sh']:
            assert (task_dir / required).is_file(), (task, required)
    descriptions = list((ROOT / 'artifacts/agentmeter_opt_final16/descriptions').glob('*/*/optimized_instruction.md'))
    assert len(descriptions) == 16
    assert len({p.parent.name for p in descriptions}) == 13
    assert len({p.parent.parent.name for p in descriptions}) == 4
    for source in {p.parent.parent.name for p in descriptions}:
        assert sum(p.parent.parent.name == source for p in descriptions) == 4
    for optimized in descriptions:
        task_dir, = (ROOT / 'benchmark_tasks').glob(f'*/{optimized.parent.name}')
        assert optimized.with_name('baseline_instruction.md').read_bytes() == (task_dir / 'instruction.md').read_bytes()
        assert optimized.stat().st_size > 0


def test_cross_grid_is_complete_and_unique():
    with (ROOT / 'artifacts/agentmeter_opt_final16/results/cross_task_results.csv').open() as f:
        rows = list(csv.DictReader(f))
    keys = [(r['task_id'], r['source_combo'], r['target_combo']) for r in rows]
    assert len(keys) == len(set(keys)) == 192
    assert all(source != target for _, source, target in keys)

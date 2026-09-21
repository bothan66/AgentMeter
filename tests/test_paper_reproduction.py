import csv
from copy import deepcopy

import pytest

from reproduce_paper_tables import ROOT, compute_tables, load_inputs, validate_grid


def short_pair(target):
    model, cli = target.split('__')
    model = {'Qwen3.6+': 'Qwen', 'MiniMax-M2.5': 'MM', 'GLM-5.1': 'GLM',
             'DeepSeek-v4-pro': 'DS', 'gpt-5.3-codex': 'GPT',
             'claude-sonnet-4-6': 'Claude', 'gemini-3.5-flash': 'Gem.'}[model]
    cli = {'kimi-cli': 'kimi', 'qwen-coder': 'qwen', 'Codex': 'Codex',
           'codex': 'Codex', 'Claude_Code': 'Claude', 'claude-code': 'Claude'}[cli]
    return f'{model}/{cli}'


def test_recompute_all_core30_paper_rows():
    core, _ = compute_tables(*load_inputs())
    with (ROOT / 'artifacts/core30_paper_results.csv').open() as f:
        reference = {r['pair']: r for r in csv.DictReader(f)}
    assert len(core) == len(reference) == 28
    for target, r in core.items():
        ref = reference[short_pair(target)]
        assert r['passes'] == int(ref['full_pass_tasks'])
        assert round(r['AMS'], 3) == float(ref['ams'])
        assert round(r['tokens'] / r['passes'] / 1e6, 2) == float(ref['tokens_per_pass_million'])
        assert round(r['cost'] / r['passes'], 3) == float(ref['usd_per_pass'])


def test_final16_matches_manuscript():
    _, final = compute_tables(*load_inputs())
    expected = {'qwen36_kimi_cli': (.353, .470, .457),
                'qwen36_codex': (.250, .457, .411),
                'deepseek_v4_kimi_cli': (.341, .457, .438),
                'glm51_qwen_coder': (.389, .446, .429)}
    for target, values in expected.items():
        assert tuple(round(final[target][c]['AMS'], 3) for c in ['Original', 'Pooled', 'Cross']) == values
        assert [final[target][c]['n'] for c in ['Original', 'Self', 'Cross', 'Pooled']] == [16, 16, 48, 64]


def test_reject_incomplete_duplicate_or_inconsistent_grid():
    rows, _ = load_inputs()
    for invalid in [rows[:-1], rows + [rows[0]]]:
        with pytest.raises(ValueError):
            validate_grid(invalid)
    altered = deepcopy(rows)
    altered[0]['stratum'] = 'Hard' if altered[0]['stratum'] != 'Hard' else 'Easy'
    with pytest.raises(ValueError):
        validate_grid(altered)

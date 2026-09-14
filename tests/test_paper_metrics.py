import pytest
from agentmeter.metrics.paper import paper_ams


def calibration():
    return dict(alpha=.6, currency='USD', strata={s: dict(budgets_usd=[1, 2], zero_reward_threshold_usd=2) for s in ['Easy', 'Medium', 'Hard']})


def test_formula_partial_rewards_and_equal_stratum_weight():
    rows = [dict(task_id='a', stratum='Easy', reward=1, cost_usd=1),
            dict(task_id='b', stratum='Easy', reward=0, cost_usd=3),
            dict(task_id='c', stratum='Medium', reward=.5, cost_usd=3),
            dict(task_id='d', stratum='Hard', reward=1, cost_usd=2)]
    result = paper_ams(rows, calibration())
    assert result['strata']['Easy']['AMS'] == pytest.approx(.25)
    assert result['strata']['Medium']['EFR'] == 0
    assert result['strata']['Hard']['AUBQC'] == .5
    assert result['AMS'] == pytest.approx((.25 + .3 + .8) / 3)


def test_missing_strata_duplicates_and_nonfinite_rejected():
    row = dict(task_id='a', stratum='Easy', reward=1, cost_usd=1)
    for rows in [[row], [row, row], [dict(row, cost_usd=float('nan'))]]:
        with pytest.raises(ValueError):
            paper_ams(rows, calibration())

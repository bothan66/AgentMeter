"""Manuscript AMS: USD budgets, zero-reward EFR, equal-stratum mean.

Input rows represent one evaluated configuration/condition and contain
task_id, stratum (Easy/Medium/Hard), reward, and cost_usd. Repeated runs must
be aggregated under an explicitly chosen protocol before calling this API.
"""
import math

CNY_TO_USD = 0.1471


def paper_ams(rows, calibration):
    rows = list(rows)
    alpha = float(calibration['alpha'])
    if not 0 <= alpha <= 1:
        raise ValueError('alpha must be in [0, 1]')
    if calibration['currency'] != 'USD':
        raise ValueError('Paper AMS requires USD')
    groups = {s: [] for s in calibration['strata']}
    seen = set()
    for row in rows:
        task = row['task_id']
        if task in seen:
            raise ValueError('Duplicate task: supply one configuration/condition at a time')
        seen.add(task)
        s = row['stratum']
        if s not in groups:
            raise ValueError(f'Unknown stratum: {s}')
        reward, cost = float(row['reward']), float(row['cost_usd'])
        if not math.isfinite(reward) or not 0 <= reward <= 1:
            raise ValueError('reward must be finite and in [0, 1]')
        if not math.isfinite(cost) or cost < 0:
            raise ValueError('cost_usd must be finite and nonnegative')
        groups[s].append((reward, cost))
    details = {}
    for s, items in groups.items():
        if not items:
            raise ValueError(f'Missing stratum: {s}; do not silently change macro weights')
        config = calibration['strata'][s]
        budgets = [float(x) for x in config['budgets_usd']]
        threshold = float(config['zero_reward_threshold_usd'])
        if not budgets or any(not math.isfinite(b) or b < 0 for b in budgets):
            raise ValueError('budgets must be finite and nonnegative')
        if not math.isfinite(threshold) or threshold < 0:
            raise ValueError('threshold must be finite and nonnegative')
        n = len(items)
        tq = sum(r for r, _ in items) / n
        aubqc = sum(sum(r for r, c in items if c <= b) / n for b in budgets) / len(budgets)
        efr = sum(r == 0 and c > threshold for r, c in items) / n
        score = (alpha * tq + (1 - alpha) * aubqc) * (1 - efr)
        details[s] = dict(n=n, TQ=tq, AUBQC=aubqc, EFR=efr, AMS=score)
    return dict(AMS=sum(v['AMS'] for v in details.values()) / len(details), strata=details,
                calibration_precision=calibration.get('precision', 'unspecified'))

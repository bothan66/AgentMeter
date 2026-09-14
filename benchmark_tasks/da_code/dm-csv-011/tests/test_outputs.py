"""DA-Code aligned scorer: emits continuous reward (no 0.99 threshold).

Mirrors the original DA-Code evaluator
(https://github.com/yiyihum/da-code, da_agent/evaluators/evaluation.py):
per-file score from compare_csv / compare_text / compare_ml, then aggregated
via metric_conj (avg/max/min/and/or). Default avg matches the upstream default.
"""
import json
import os
import sys
import traceback

sys.path.insert(0, "/tests")
from da_metrics import compare_csv, compare_text, compare_ml

GOLD_DIR = "/tests/gold"
OUTPUT_DIR = "/app/output"
REWARD_PATH = "/logs/verifier/reward.txt"

with open("/tests/eval_config.json") as _f:
    cfg = json.load(_f)

FUNC = cfg["func"]
RESULT_FILES = cfg["result_files"]
OPTIONS = cfg.get("options", {}) or {}
ML_CONFIG = cfg.get("ml_config", {}) or {}
CONJ = cfg.get("metric_conj", "avg")


def score_one(rf: str) -> tuple[float, list[str]]:
    out_path = os.path.join(OUTPUT_DIR, rf)
    gold_path = os.path.join(GOLD_DIR, rf)
    if not os.path.exists(out_path):
        return 0.0, [f"missing output: {rf}"]
    try:
        if FUNC == "compare_csv":
            if not os.path.exists(gold_path):
                return 0.0, [f"missing gold: {rf}"]
            s = compare_csv(out_path, [gold_path], **OPTIONS)
            return float(s), []
        if FUNC == "compare_text":
            if not os.path.exists(gold_path):
                return 0.0, [f"missing gold: {rf}"]
            r = compare_text(out_path, gold_path, **OPTIONS)
            if isinstance(r, dict):
                return float(r.get("score", 0.0)), list(r.get("errors", []))
            return float(r or 0.0), []
        if FUNC == "compare_ml":
            gold_arg = [gold_path] if os.path.exists(gold_path) else []
            r = compare_ml(out_path, gold_arg, config=ML_CONFIG, **OPTIONS)
            if isinstance(r, dict):
                return float(r.get("score", 0.0)), list(r.get("errors", []))
            return float(r or 0.0), []
        return 0.0, [f"unknown func: {FUNC}"]
    except Exception as e:
        traceback.print_exc()
        return 0.0, [f"exception: {e}"]


def aggregate(scores: list[float], conj: str) -> float:
    if not scores:
        return 0.0
    if conj == "max":
        return max(scores)
    if conj == "min":
        return min(scores)
    if conj == "and":
        return float(all(s != 0 for s in scores))
    if conj == "or":
        return float(any(s != 0 for s in scores))
    return sum(scores) / len(scores)


def main() -> None:
    os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
    scores, all_errors = [], []
    for rf in RESULT_FILES:
        s, errs = score_one(rf)
        scores.append(s)
        all_errors.extend(f"{rf}: {e}" for e in errs)
        print(f"[score] {rf}: {s:.4f}  errors={errs}")
    total = aggregate(scores, CONJ)
    print(f"[total] conj={CONJ} per_file={scores} -> {total:.6f}")
    if all_errors:
        print(f"[errors] {all_errors}")
    with open(REWARD_PATH, "w") as f:
        f.write(f"{total:.6f}\n")


if __name__ == "__main__":
    main()

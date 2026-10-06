"""Read baseline outcomes and construct feedback for successive rewrite rounds."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

from agentmeter.harness import read_json

from .evidence import build_trajectory_evidence
from .text import compact, diff_summary


def load_baseline_result(path: Path | None, task_id: str, combo: str) -> dict[str, Any]:
    """Read runner or Harbor outcomes using the original experiment's token conventions."""
    baseline = {
        "baseline_passed": False,
        "baseline_reward": 0.0,
        "baseline_tokens": 0,
        "baseline_tool_calls": 0,
        "baseline_turns": 0,
        "trajectory_summary": "",
        "trajectory_evidence": build_trajectory_evidence(path),
        "source_path": str(path) if path else "",
    }
    if not path or not path.exists():
        return baseline

    def update_from_dict(data: dict[str, Any]) -> None:
        final_metrics = (
            data.get("final_metrics") if isinstance(data.get("final_metrics"), dict) else {}
        )
        total_tokens = (
            data.get("total_tokens")
            or data.get("tokens")
            or (
                (data.get("agent_result") or {}).get("total_tokens")
                if isinstance(data.get("agent_result"), dict)
                else 0
            )
            or final_metrics.get("total_tokens")
            or (
                int(final_metrics.get("total_prompt_tokens") or 0)
                + int(final_metrics.get("total_completion_tokens") or 0)
                + int(final_metrics.get("total_cached_tokens") or 0)
            )
        )
        verifier_reward = None
        verifier_result = data.get("verifier_result")
        if isinstance(verifier_result, dict):
            rewards = verifier_result.get("rewards")
            if isinstance(rewards, dict):
                verifier_reward = rewards.get("reward")
        reward_value = data.get("reward")
        if reward_value is None and verifier_reward is not None:
            reward_value = verifier_reward
        passed_value = data.get("passed")
        if passed_value is None and reward_value is not None:
            passed_value = float(reward_value) >= 1.0
        baseline["baseline_passed"] = bool(passed_value)
        baseline["baseline_reward"] = float(reward_value or (1.0 if passed_value else 0.0) or 0.0)
        if total_tokens or not baseline["baseline_tokens"]:
            baseline["baseline_tokens"] = int(total_tokens or 0)
        tool_calls_value = data.get("tool_calls")
        if tool_calls_value or not baseline["baseline_tool_calls"]:
            baseline["baseline_tool_calls"] = int(tool_calls_value or 0)
        steps_value = data.get("steps")
        if isinstance(steps_value, list):
            steps_value = len(steps_value)
        turns_value = data.get("turns") or steps_value or final_metrics.get("total_steps") or 0
        if turns_value or not baseline["baseline_turns"]:
            baseline["baseline_turns"] = int(turns_value or 0)
        summary_value = compact(
            data.get("verifier_summary")
            or data.get("final_error")
            or data.get("error")
            or data.get("run_dir")
            or "",
            500,
        )
        if summary_value or not baseline["trajectory_summary"]:
            baseline["trajectory_summary"] = summary_value

    def update_from_trial_dir(trial_dir: Path) -> bool:
        found = False
        for name in ["summary.json", "result.json", "raw_task_facts.json", "task_result.json"]:
            candidate = trial_dir / name
            if candidate.exists():
                update_from_dict(read_json(candidate))
                found = True
                break
        reward_txt = trial_dir / "verifier" / "reward.txt"
        if reward_txt.exists():
            try:
                reward_value = float(reward_txt.read_text(encoding="utf-8").strip())
                baseline["baseline_reward"] = reward_value
                baseline["baseline_passed"] = reward_value >= 1.0
                found = True
            except Exception:
                pass
        return found

    if path.is_dir():
        if update_from_trial_dir(path):
            return baseline
        if (path / "trajectory.jsonl").exists():
            baseline["trajectory_summary"] = "trajectory.jsonl present"
            return baseline
        return baseline

    if path.suffix.lower() == ".json":
        update_from_dict(read_json(path))
        if path.name == "trajectory.json":
            trial_dir = path.parent.parent if path.parent.name == "agent" else path.parent
            update_from_trial_dir(trial_dir)
        return baseline
    if path.suffix.lower() == ".jsonl":
        rows = []
        with path.open(encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if raw:
                    rows.append(json.loads(raw))
        for row in rows:
            if str(row.get("task_id") or "") == task_id and str(row.get("combo") or combo) == combo:
                update_from_dict(row)
                return baseline
        if rows and isinstance(rows[0], dict):
            update_from_dict(rows[0])
        return baseline
    return baseline


def trial_dir_for_result_path(path: Path | None) -> Path | None:
    """Locate trial artifacts beside a result file or the agent's trajectory file."""
    if not path:
        return None
    if path.is_dir():
        return path
    if path.name == "trajectory.json" and path.parent.name == "agent":
        return path.parent.parent
    if path.name in {"result.json", "summary.json", "task_result.json", "raw_task_facts.json"}:
        return path.parent
    return path.parent if path.exists() else None


def trajectory_path_for_result(path: Path | None) -> Path | None:
    if not path:
        return None
    if path.name == "trajectory.json" and path.exists():
        return path
    trial_dir = trial_dir_for_result_path(path)
    if not trial_dir:
        return None
    candidate = trial_dir / "agent" / "trajectory.json"
    return candidate if candidate.exists() else None


def load_cost_summary(path: Path | None) -> dict[str, Any]:
    """Prefer archived costs; otherwise retain the experiment's historical cache pricing."""
    trial_dir = trial_dir_for_result_path(path)
    if not trial_dir:
        return {"available": False}
    cost_path = trial_dir / "cost.json"
    if not cost_path.exists():
        result_path = trial_dir / "result.json"
        if result_path.exists():
            try:
                result = read_json(result_path)
                agent_result = (
                    result.get("agent_result")
                    if isinstance(result.get("agent_result"), dict)
                    else {}
                )
                input_total = int(agent_result.get("n_input_tokens") or 0)
                cache_hit = int(agent_result.get("n_cache_tokens") or 0)
                output = int(agent_result.get("n_output_tokens") or 0)
                if input_total or cache_hit or output:
                    input_pure = max(0, input_total - cache_hit)
                    billable = (
                        input_pure * 6 / 1_000_000
                        + cache_hit * 1.2 / 1_000_000
                        + output * 24 / 1_000_000
                    )
                    return {
                        "available": True,
                        "cost_path": str(cost_path),
                        "cost_source": "result_json_agent_result_no_tier_cache_discount",
                        "billable_cost_cny": billable,
                        "input_pure_tokens": input_pure,
                        "cache_creation_tokens": 0,
                        "cache_hit_tokens": cache_hit,
                        "output_tokens": output,
                        "input_total_tokens": input_total,
                    }
            except Exception as exc:
                return {
                    "available": False,
                    "cost_path": str(cost_path),
                    "error": compact(str(exc), 300),
                }
        trajectory_path = trial_dir / "agent" / "trajectory.json"
        if trajectory_path.exists():
            try:
                trajectory = read_json(trajectory_path)
                final = (
                    trajectory.get("final_metrics")
                    if isinstance(trajectory.get("final_metrics"), dict)
                    else {}
                )
                input_total = int(
                    final.get("total_prompt_tokens") or final.get("total_input_tokens") or 0
                )
                cache_hit = int(final.get("total_cached_tokens") or 0)
                output = int(
                    final.get("total_completion_tokens") or final.get("total_output_tokens") or 0
                )
                if input_total or cache_hit or output:
                    input_pure = max(0, input_total - cache_hit)
                    billable = (
                        input_pure * 6 / 1_000_000
                        + cache_hit * 1.2 / 1_000_000
                        + output * 24 / 1_000_000
                    )
                    return {
                        "available": True,
                        "cost_path": str(cost_path),
                        "cost_source": "trajectory_final_metrics_no_tier_cache_discount",
                        "billable_cost_cny": billable,
                        "input_pure_tokens": input_pure,
                        "cache_creation_tokens": 0,
                        "cache_hit_tokens": cache_hit,
                        "output_tokens": output,
                        "input_total_tokens": input_total,
                    }
            except Exception as exc:
                return {
                    "available": False,
                    "cost_path": str(cost_path),
                    "error": compact(str(exc), 300),
                }
        return {"available": False, "cost_path": str(cost_path)}
    try:
        data = read_json(cost_path)
    except Exception as exc:
        return {"available": False, "cost_path": str(cost_path), "error": compact(str(exc), 300)}
    tokens = data.get("tokens") if isinstance(data.get("tokens"), dict) else {}
    cost = data.get("cost_cny") if isinstance(data.get("cost_cny"), dict) else {}
    return {
        "available": True,
        "cost_path": str(cost_path),
        "billable_cost_cny": cost.get("total"),
        "input_pure_tokens": tokens.get("input_pure"),
        "cache_creation_tokens": tokens.get("cache_creation"),
        "cache_hit_tokens": tokens.get("cache_hit") or tokens.get("cache_hit_observed"),
        "output_tokens": tokens.get("output"),
        "input_total_tokens": tokens.get("input_total"),
    }


def _optional_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _percent_change(baseline_value: float | None, current_value: float | None) -> float | None:
    """Measure relative change, returning None when a percentage is undefined."""
    if baseline_value in (None, 0) or current_value is None:
        return None
    return ((current_value - baseline_value) / baseline_value) * 100.0


def build_round_feedback(
    *,
    adaptation_mode: str,
    round_index: int,
    original_instruction: str,
    seed_instruction: str,
    baseline: dict[str, Any],
    baseline_result: Path | None,
    previous_result: Path | None,
    public_instruction: str,
    max_events: int,
) -> dict[str, Any]:
    """Build iterative feedback for round >= 2.

    This is intentionally generic: it compares the previous accepted rewrite's
    real rerun against the original baseline and converts the observed outcome
    into the next round objective. The final winner is still selected by real
    reward/cost reruns, not by this offline diagnostic.
    """
    baseline_cost = load_cost_summary(baseline_result)
    previous = load_baseline_result(previous_result, "", "") if previous_result else {}
    previous_traj = trajectory_path_for_result(previous_result)
    previous_cost = load_cost_summary(previous_result)
    if previous_result:
        previous["trajectory_evidence"] = build_trajectory_evidence(
            previous_traj or previous_result,
            public_instruction=public_instruction,
            max_events=max_events,
        )
    baseline_reward = _optional_float(baseline.get("baseline_reward"))
    previous_reward = _optional_float(previous.get("baseline_reward"))
    baseline_bill = _optional_float(baseline_cost.get("billable_cost_cny"))
    previous_bill = _optional_float(previous_cost.get("billable_cost_cny"))
    reward_delta = (
        None
        if baseline_reward is None or previous_reward is None
        else previous_reward - baseline_reward
    )
    cost_delta_pct = _percent_change(baseline_bill, previous_bill)
    seed_diff = diff_summary(original_instruction, seed_instruction)
    if not previous_result and adaptation_mode == "generic_no_trajectory":
        failure_type = ""
        objective = "generic_rewrite_from_public_instruction_only"
        guidance = [
            "No prior trajectory or rerun feedback is available for this mode.",
            "Use only the original public instruction and the current seed instruction to propose a safe, clearer rewrite.",
        ]
    elif not previous_result:
        # Round 1 has no previous rerun by design. Do not treat that as a
        # refinement failure, otherwise candidate-only mode incorrectly
        # rejects no-op/seed candidates as if a failed rewrite needed repair.
        failure_type = ""
        objective = "adapt_from_baseline"
        guidance = ["No previous rerun was supplied; optimize from the baseline trajectory only."]
    elif reward_delta is not None and reward_delta < -1e-9:
        failure_type = "reward_down"
        objective = "restore_reward_after_regression"
        guidance = [
            "The previous rewrite reduced reward. Preserve useful public clarifications only if they do not change the original task semantics.",
            "Remove or soften additions that may have changed output contract, task objective, public I/O, or required interpretation.",
            "The next rewrite should recover reward first; cost is secondary until reward no longer regresses.",
        ]
    elif (
        reward_delta is not None
        and abs(reward_delta) <= 1e-9
        and cost_delta_pct is not None
        and cost_delta_pct > 1e-9
    ):
        failure_type = "reward_same_cost_up"
        objective = "reduce_cost_after_no_reward_gain"
        guidance = [
            "The previous rewrite did not improve reward and increased billable cost. Make the next rewrite shorter and less route-expanding.",
            "Keep only public clarifications directly tied to repeated reads, command loops, output-format hesitation, or delayed stopping.",
            "Do not add extra validation, analysis standards, domain preferences, or verbose explanations.",
        ]
    elif (
        reward_delta is not None
        and reward_delta > 1e-9
        and cost_delta_pct is not None
        and cost_delta_pct > 10.0
    ):
        failure_type = "reward_up_cost_up"
        objective = "compact_successful_rewrite"
        guidance = [
            "The previous rewrite improved reward but increased cost. Preserve the likely reward-critical public clarifications and compress everything else.",
            "Do not remove the output/interface clarifications that plausibly caused the reward gain.",
        ]
    elif reward_delta is not None and reward_delta > 1e-9:
        failure_type = "reward_up"
        objective = "keep_or_lightly_compact_success"
        guidance = [
            "The previous rewrite improved reward. Prefer keeping it or lightly compacting without changing semantics."
        ]
    elif cost_delta_pct is not None and cost_delta_pct < -1e-9:
        failure_type = "reward_same_cost_down"
        objective = "stop_or_light_compact"
        guidance = [
            "The previous rewrite already reduced cost without reward loss. A further round should be minimal or no-op."
        ]
    else:
        failure_type = "no_measurable_gain"
        objective = "rescue_failed_prompt_adaptation"
        guidance = [
            "The previous rewrite did not produce measurable reward or cost gain. Re-examine whether the issue is actually prompt-adaptable.",
            "If the trajectory suggests solver-heavy, environment, or hidden-evaluator dominance, keep the rewrite minimal.",
        ]
    return {
        "round_index": round_index,
        "round_objective": objective,
        "failure_type": failure_type,
        "baseline_result_path": str(baseline_result) if baseline_result else "",
        "previous_result_path": str(previous_result) if previous_result else "",
        "previous_trajectory_path": str(previous_traj) if previous_traj else "",
        "baseline_reward": baseline_reward,
        "previous_reward": previous_reward,
        "reward_delta_vs_baseline": reward_delta,
        "baseline_billable_cost_cny": baseline_bill,
        "previous_billable_cost_cny": previous_bill,
        "cost_delta_pct_vs_baseline": cost_delta_pct,
        "baseline_cost_summary": baseline_cost,
        "previous_cost_summary": previous_cost,
        "seed_instruction_diff_summary": seed_diff,
        "previous_rerun_summary": {k: v for k, v in previous.items() if k != "trajectory_evidence"},
        "previous_rerun_trajectory_evidence": previous.get("trajectory_evidence", {}),
        "round_guidance": guidance,
        "best_so_far_policy": "Select by highest real reward first; if reward ties, choose lower billable cost; if still close, prefer smaller safe instruction diff.",
    }


def round_objective_suffix(round_feedback: dict[str, Any]) -> str:
    if not round_feedback or round_feedback.get("round_index", 1) <= 1:
        return ""
    guidance = "\n".join(f"- {item}" for item in (round_feedback.get("round_guidance") or []))
    return textwrap.dedent(f"""

    Iterative optimization round {round_feedback.get("round_index")}: {round_feedback.get("round_objective")}

    The previous accepted rewrite has already been rerun. Use the previous rerun result as feedback, not as a hidden answer source.
    Observed previous-round failure type: {round_feedback.get("failure_type")}.
    Baseline reward: {round_feedback.get("baseline_reward")}; previous rewrite reward: {round_feedback.get("previous_reward")}; reward delta: {round_feedback.get("reward_delta_vs_baseline")}.
    Baseline billable cost CNY: {round_feedback.get("baseline_billable_cost_cny")}; previous rewrite billable cost CNY: {round_feedback.get("previous_billable_cost_cny")}; cost delta pct: {round_feedback.get("cost_delta_pct_vs_baseline")}.

    Current round guidance:
    {guidance}

    Keep the output as a complete final instruction.md. Do not mention rounds, previous runs, costs, trajectories, model/CLI, hidden evaluators, tests, checker behavior, or gold answers in the rewritten instruction.
    """).strip()

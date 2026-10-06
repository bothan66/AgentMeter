"""Coordinate trajectory-guided rewriting, safety checks, and GEPA candidate selection."""

from __future__ import annotations

import argparse
import difflib
import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentmeter.harness import read_json, reported_reward, write_json

from .costs import cost_summary_from_mapping, load_cost_summary
from .evidence import build_public_only_evidence, build_trajectory_evidence
from .execution import run_agent_task
from .feedback import build_round_feedback, load_baseline_result, round_objective_suffix
from .policy import (
    adaptation_policy_for_baseline,
    baseline_efficiency_friction,
    candidate_only_acceptance_score,
    objective_for_mode,
    rejection_feedback_from_safety,
    safety_gate_for_mode,
)
from .providers import (
    clear_proxy_environment,
    configure_gepa_call,
    configure_reflection_provider_environment,
    detect_gepa,
    discover_runner_config,
    extract_best_candidate,
    parse_combo,
    runner_has_route,
)
from .selection import CandidateOutcome, retain_candidate
from .text import compact, diff_summary, ensure_empty_dir, safe_name, write_text


@dataclass
class _EvaluationCounts:
    """Track candidate evaluations separately from live agent reruns."""

    metric_calls: int = 0
    real_reruns: int = 0


def _parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    """Parse the optimization command and validate inputs before any file writes."""
    parser = argparse.ArgumentParser(prog="agentmeter optimize", description=__doc__)
    parser.add_argument("--task-id", default="dm-csv-001")
    parser.add_argument("--task-root", type=Path, required=True)
    parser.add_argument(
        "--seed-instruction",
        type=Path,
        help="Optional previous accepted rewritten instruction to use as GEPA seed. Safety is still checked against the original task instruction.",
    )
    parser.add_argument(
        "--baseline-result", type=Path, help="Observed outcome of the original task instruction."
    )
    parser.add_argument(
        "--previous-result",
        type=Path,
        help="Previous accepted rewrite rerun result/trajectory for iterative round feedback.",
    )
    parser.add_argument(
        "--round-index",
        type=int,
        default=1,
        help="1 for baseline adaptation; >=2 for iterative feedback repair/compaction rounds.",
    )
    parser.add_argument("--combo", default="qwen36_kimi_cli")
    parser.add_argument("--model")
    parser.add_argument("--cli")
    parser.add_argument("--runner-config", type=Path)
    parser.add_argument(
        "--eval-command",
        help="Command that verifies the rewritten agent run in {task_dir}; required for live reruns.",
    )
    parser.add_argument("--max-metric-calls", type=int, default=5)
    parser.add_argument("--max-real-reruns", type=int, default=2)
    parser.add_argument(
        "--candidate-only",
        action="store_true",
        help="Do not run the agent; select safe rewritten instruction candidates for later benchmark validation.",
    )
    parser.add_argument(
        "--offline-until-accepted",
        action="store_true",
        help="In candidate-only mode, continue offline GEPA proposals until an accepted candidate is found or max metric calls is reached.",
    )
    parser.add_argument(
        "--adaptation-mode",
        choices=["strict", "combo_adapted", "generic_no_trajectory"],
        default="strict",
    )
    parser.add_argument("--default-timeout-sec", type=int, default=900)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--reflection-model")
    parser.add_argument("--max-trajectory-evidence-events", type=int, default=10)
    parser.add_argument(
        "--allow-proxy",
        action="store_true",
        help="Keep HTTP(S)/ALL_PROXY environment variables for reflection LLM calls. By default they are cleared.",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("generated_reports/agentmeter_opt_min")
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.task_id):
        parser.error("--task-id must be a single task name, without path components")

    if not (args.candidate_only or args.dry_run) and not args.eval_command:
        parser.error(
            "--eval-command is required for live reruns; it must verify the agent-produced outputs."
        )
    return args


def main(argv: list[str] | None = None) -> None:
    """Optimize one public task instruction using recorded trajectory feedback."""
    args = _parse_arguments(argv)

    if args.adaptation_mode == "generic_no_trajectory" and not args.model and not args.cli:
        model, cli = "generic-public-rewrite", "generic-public-rewrite"
    else:
        model, cli = parse_combo(args.combo, args.model, args.cli)
    runner_config = discover_runner_config(args.runner_config)
    runner_connected = runner_has_route(runner_config, model, cli)
    task_dir = (args.task_root / args.task_id).resolve()
    original_instruction_path = task_dir / "instruction.md"
    if not original_instruction_path.exists():
        raise SystemExit(f"instruction.md not found: {original_instruction_path}")
    removed_proxy_env = {} if args.allow_proxy else clear_proxy_environment()
    reflection_provider_env = configure_reflection_provider_environment(args.reflection_model)

    result_dir = args.out_dir / safe_name(args.task_id) / safe_name(args.combo)
    original_instruction = original_instruction_path.read_text(encoding="utf-8")
    seed_instruction_path = (
        args.seed_instruction.resolve() if args.seed_instruction else original_instruction_path
    )
    if not seed_instruction_path.exists():
        raise SystemExit(f"seed instruction not found: {seed_instruction_path}")
    seed_instruction = seed_instruction_path.read_text(encoding="utf-8")
    baseline = load_baseline_result(args.baseline_result, args.task_id, args.combo)
    baseline_cost = load_cost_summary(args.baseline_result)
    original_outcome = CandidateOutcome(
        candidate_id="original",
        instruction=original_instruction,
        reward=baseline["baseline_reward"],
        passed=baseline["baseline_passed"] if baseline["baseline_reward"] is not None else None,
        cost_usd=baseline_cost["billable_cost_usd"],
        cost_cny=baseline_cost["billable_cost_cny"],
    )
    if args.adaptation_mode == "generic_no_trajectory":
        baseline["trajectory_evidence"] = build_public_only_evidence(original_instruction)
    else:
        baseline["trajectory_evidence"] = build_trajectory_evidence(
            args.baseline_result,
            public_instruction=original_instruction,
            max_events=max(1, args.max_trajectory_evidence_events),
        )
    efficiency_friction = baseline_efficiency_friction(baseline)
    adaptation_policy = adaptation_policy_for_baseline(baseline, args.adaptation_mode)
    round_feedback = build_round_feedback(
        adaptation_mode=args.adaptation_mode,
        round_index=max(1, int(args.round_index or 1)),
        original_instruction=original_instruction,
        seed_instruction=seed_instruction,
        baseline=baseline,
        baseline_result=args.baseline_result,
        previous_result=args.previous_result,
        public_instruction=original_instruction,
        max_events=max(1, args.max_trajectory_evidence_events),
    )
    objective = objective_for_mode(
        args.adaptation_mode, baseline_passed=bool(baseline["baseline_passed"])
    )
    suffix = round_objective_suffix(round_feedback)
    if suffix:
        objective = objective + "\n\n" + suffix
    gepa_info = detect_gepa()
    setup = {
        "task_id": args.task_id,
        "combo": args.combo,
        "model": model,
        "cli": cli,
        "task_root": str(args.task_root.resolve()),
        "task_dir": str(task_dir),
        "original_instruction_path": str(original_instruction_path),
        "seed_instruction_path": str(seed_instruction_path),
        "seed_differs_from_original": seed_instruction != original_instruction,
        "baseline_result": str(args.baseline_result) if args.baseline_result else "",
        "feedback_result_path": str(args.baseline_result) if args.baseline_result else "",
        "previous_result_path": str(args.previous_result) if args.previous_result else "",
        "round_index": int(args.round_index or 1),
        "round_objective": round_feedback.get("round_objective"),
        "round_failure_type": round_feedback.get("failure_type"),
        "safety_reference_instruction_path": str(original_instruction_path),
        "runner_config": str(runner_config) if runner_config else "",
        "runner_connected": runner_connected,
        "adaptation_mode": args.adaptation_mode,
        "baseline_mode": adaptation_policy["baseline_mode"],
        "candidate_only": bool(args.candidate_only),
        "offline_until_accepted": bool(args.offline_until_accepted),
        "objective": objective,
        "proxy_env_cleared": not args.allow_proxy,
        "removed_proxy_env_keys": sorted(removed_proxy_env),
        "reflection_provider_env": reflection_provider_env,
        "gepa_info": gepa_info,
    }
    protected_inputs = [task_dir, original_instruction_path, seed_instruction_path]
    protected_inputs.extend(
        path for path in (args.baseline_result, args.previous_result, runner_config) if path
    )
    ensure_empty_dir(
        result_dir, args.overwrite, output_root=args.out_dir, protected_paths=protected_inputs
    )
    write_json(result_dir / "gepa_setup.json", setup)
    write_json(result_dir / "baseline.json", baseline)
    write_json(result_dir / "baseline_trajectory_evidence.json", baseline["trajectory_evidence"])
    write_json(result_dir / "baseline_efficiency_friction.json", efficiency_friction)
    write_json(result_dir / "round_feedback.json", round_feedback)
    write_text(result_dir / "original_instruction.md", original_instruction)
    write_text(result_dir / "seed_instruction.md", seed_instruction)

    if args.dry_run:
        dry = {
            "task_id": args.task_id,
            "combo": args.combo,
            "runner_connected": runner_connected,
            "gepa_installed": bool(gepa_info["installed"]),
            "status": "dry_run_only",
        }
        write_json(result_dir / "gepa_task_result.json", dry)
        print(json.dumps(dry, indent=2))
        return

    if not gepa_info["installed"]:
        raise SystemExit(
            "GEPA is not installed. Install official package first: `pip install gepa` or `pip install git+https://github.com/gepa-ai/gepa.git`."
        )
    if not args.candidate_only:
        if not runner_config:
            raise SystemExit(
                "no runner config found; pass --runner-config or create configs/runners.local.yaml"
            )
        if not runner_connected:
            raise SystemExit(
                f"runner config {runner_config} does not provide a route for model={model!r}, cli={cli!r}"
            )

    gepa_optimizer = importlib.import_module("gepa.optimize_anything")
    optimize_anything = getattr(gepa_optimizer, "optimize_anything")
    optimize_kwargs, api_meta = configure_gepa_call(gepa_optimizer, args, result_dir)
    setup["gepa_info"]["resolved_api"] = api_meta
    write_json(result_dir / "gepa_setup.json", setup)

    evaluation_counts = _EvaluationCounts()
    history: list[dict[str, Any]] = []
    candidate_cache: dict[str, dict[str, Any]] = {}
    measured_candidates: list[CandidateOutcome] = []
    rejection_feedback_memory: list[dict[str, Any]] = []

    def evaluator(candidate: str) -> float:
        evaluation_counts.metric_calls += 1
        # Reuse a measurement only for exactly the same instruction. Collapsing
        # whitespace could conflate distinct code blocks or Markdown structure.
        candidate_key = candidate
        call_dir = result_dir / "metric_calls" / f"metric_call_{evaluation_counts.metric_calls:03d}"
        call_dir.mkdir(parents=True, exist_ok=True)
        write_text(call_dir / "rewritten_instruction.md", candidate)
        diff = diff_summary(original_instruction, candidate)
        write_text(
            call_dir / "instruction.diff",
            "\n".join(
                difflib.unified_diff(
                    original_instruction.splitlines(),
                    candidate.splitlines(),
                    fromfile="original/instruction.md",
                    tofile="rewritten/instruction.md",
                    lineterm="",
                )
            ),
        )
        write_json(call_dir / "diff_summary.json", diff)

        safety = safety_gate_for_mode(args.adaptation_mode, original_instruction, candidate)
        write_json(call_dir / "safety_gate.json", safety)

        side_info = {
            "adaptation_mode": args.adaptation_mode,
            "baseline_mode": adaptation_policy["baseline_mode"],
            "policy": adaptation_policy["policy"],
            "optimization_target": adaptation_policy["optimization_target"],
            "adaptation_goal": adaptation_policy["adaptation_goal"],
            "agent_efficiency_goal": adaptation_policy["agent_efficiency_goal"],
            "trajectory_rewrite_guidance": adaptation_policy["trajectory_rewrite_guidance"],
            "uses_trajectory_feedback": adaptation_policy.get("uses_trajectory_feedback", True),
            "baseline_trajectory_evidence": baseline["trajectory_evidence"]
            if adaptation_policy.get("uses_trajectory_feedback", True)
            else {},
            "safety_result": safety,
            "semantic_preservation_status": safety.get("semantic_preservation_status"),
            "core_actions_original": safety.get("core_actions_original", []),
            "core_actions_rewritten": safety.get("core_actions_rewritten", []),
            "core_task_drift": safety.get("core_task_drift", []),
            "unsupported_added_preferences": safety.get("unsupported_added_preferences", []),
            "diff_summary": diff,
            "baseline_tokens": baseline["baseline_tokens"],
            "baseline_passed": baseline["baseline_passed"],
            "baseline_efficiency_friction": efficiency_friction,
            "trajectory_summary": baseline["trajectory_summary"]
            if adaptation_policy.get("uses_trajectory_feedback", True)
            else "",
            "previous_rejection_feedback": rejection_feedback_memory[-3:],
            "round_feedback": round_feedback,
            "round_objective": round_feedback.get("round_objective"),
            "round_failure_type": round_feedback.get("failure_type"),
            "seed_instruction_differs_from_original": setup["seed_differs_from_original"],
            "safety_reference_policy": "All candidates are checked against the original public instruction, even when GEPA starts from a previous accepted rewritten instruction.",
            "feedback_source": {
                "baseline_result": str(args.baseline_result) if args.baseline_result else "",
                "meaning": (
                    "No trajectory/result feedback is used in this mode; optimization is based only on the original public instruction and the task-preservation safety gate."
                    if not adaptation_policy.get("uses_trajectory_feedback", True)
                    else "Use the original instruction's trajectory/result as the fixed baseline. Supply a previous accepted rewrite's result separately through --previous-result for multi-round feedback."
                ),
            },
        }
        if hasattr(gepa_optimizer, "log"):
            gepa_optimizer.log("safety_result=" + json.dumps(safety, ensure_ascii=False))
            gepa_optimizer.log("diff_summary=" + json.dumps(diff, ensure_ascii=False))
            if adaptation_policy.get("uses_trajectory_feedback", True):
                gepa_optimizer.log(
                    "trajectory_efficiency_feedback="
                    + json.dumps(
                        {
                            "route_profile": baseline["trajectory_evidence"].get(
                                "route_profile", {}
                            ),
                            "friction_signals": baseline["trajectory_evidence"].get(
                                "friction_signals", []
                            ),
                            "rewrite_guidance": baseline["trajectory_evidence"].get(
                                "rewrite_guidance", []
                            ),
                            "route_decision_points": baseline["trajectory_evidence"].get(
                                "route_decision_points", []
                            ),
                            "evidence_chains": baseline["trajectory_evidence"].get(
                                "evidence_chains", []
                            ),
                            "previous_rejection_feedback": rejection_feedback_memory[-3:],
                        },
                        ensure_ascii=False,
                    )
                )
            else:
                gepa_optimizer.log(
                    "public_only_rewrite_mode="
                    + json.dumps(
                        {
                            "uses_trajectory_feedback": False,
                            "previous_rejection_feedback": rejection_feedback_memory[-3:],
                        },
                        ensure_ascii=False,
                    )
                )
            gepa_optimizer.log("round_feedback=" + json.dumps(round_feedback, ensure_ascii=False))
            gepa_optimizer.log(
                "baseline_summary="
                + json.dumps(
                    {key: value for key, value in baseline.items() if key != "trajectory_evidence"},
                    ensure_ascii=False,
                )
            )

        rerun_info = None
        cached = candidate_cache.get(candidate_key)
        if cached:
            score = float(cached["score"])
            side_info.update(cached["side_info"])
            side_info["score_reason"] = "cached_" + str(
                side_info.get("score_reason") or "evaluation"
            )
            rerun_info = cached.get("rerun_info")
        elif safety["status"] == "fail":
            score = 0.0
            side_info["score_reason"] = "safety_fail"
            side_info["rejection_feedback_for_next_candidate"] = rejection_feedback_from_safety(
                safety
            )
        elif safety["status"] == "needs_manual_review":
            score = 0.0
            side_info["score_reason"] = "needs_manual_review"
            side_info["rejection_feedback_for_next_candidate"] = rejection_feedback_from_safety(
                safety
            )
        elif not diff["changed"]:
            should_explore_efficiency = (
                bool(baseline["baseline_passed"])
                and args.adaptation_mode == "combo_adapted"
                and bool(efficiency_friction.get("has_efficiency_friction"))
            )
            needs_round_refinement = bool(round_feedback.get("failure_type"))
            if args.candidate_only and needs_round_refinement:
                score = 0.15
                score_reason = "no_op_rejected_for_round_refinement"
            elif args.candidate_only:
                score = 0.25 if baseline["baseline_passed"] else 0.0
                score_reason = "no_op_low_score_candidate_only"
            else:
                score = 0.35 if should_explore_efficiency else (original_outcome.reward or 0.0)
                score_reason = (
                    "baseline_passed_but_efficiency_friction_explore_rewrite"
                    if should_explore_efficiency
                    else "baseline_seed_candidate_no_rerun"
                )
            side_info.update(
                {
                    "passed": original_outcome.passed,
                    "reward": original_outcome.reward,
                    "cost_summary": baseline_cost,
                    "tokens": int(baseline["baseline_tokens"] or 0),
                    "tool_calls": int(baseline["baseline_tool_calls"] or 0),
                    "token_efficiency_bonus": 0.0,
                    "score_reason": score_reason,
                    "rejection_feedback_for_next_candidate": {
                        "reason": "The candidate is identical to the original instruction. For this refinement round, propose a safe changed instruction that addresses the previous rerun regression or cost increase.",
                        "round_objective": round_feedback.get("round_objective"),
                        "failure_type": round_feedback.get("failure_type"),
                        "allowed_fix": "Keep the same task interface, but rewrite public-facing requirements, output/completion conditions, or organization to reduce the observed route friction.",
                    }
                    if args.candidate_only
                    else {},
                }
            )
        elif args.candidate_only:
            score, reason = candidate_only_acceptance_score(diff, safety)
            side_info.update(
                {
                    "passed": None,
                    "reward": None,
                    "tokens": None,
                    "tool_calls": None,
                    "token_efficiency_bonus": 0.0,
                    "score_reason": reason,
                    "candidate_only": True,
                }
            )
        elif evaluation_counts.real_reruns >= args.max_real_reruns:
            score = 0.0
            side_info["score_reason"] = "rerun_budget_exhausted"
        else:
            evaluation_counts.real_reruns += 1
            try:
                rerun_info = run_agent_task(
                    original_task_root=args.task_root.resolve(),
                    task_id=args.task_id,
                    rewritten_instruction=candidate,
                    runner_config=runner_config,
                    model=model,
                    cli=cli,
                    eval_command=args.eval_command,
                    default_timeout_sec=args.default_timeout_sec,
                    attempt=args.attempt,
                    run_root=call_dir,
                )
                rerun_summary = rerun_info["summary"]
                reward = reported_reward(rerun_summary)
                if reward is None and isinstance(rerun_summary.get("passed"), bool):
                    # Compatibility with older binary verifiers, not execution status.
                    reward = float(rerun_summary["passed"])
                passed = reward >= 1.0 if reward is not None else None
                rerun_dir = rerun_info.get("run_dir")
                recorded_cost_path = Path(rerun_dir) / "cost.json" if rerun_dir else None
                cost = (
                    load_cost_summary(recorded_cost_path)
                    if recorded_cost_path is not None and recorded_cost_path.is_file()
                    else cost_summary_from_mapping(rerun_summary, source="rerun_summary")
                )
                outcome = CandidateOutcome(
                    candidate_id=call_dir.name,
                    instruction=candidate,
                    reward=reward,
                    passed=passed,
                    cost_usd=cost["billable_cost_usd"],
                    cost_cny=cost["billable_cost_cny"],
                )
                rerun_tokens = int(rerun_summary.get("total_tokens") or 0)
                bonus = 0.0
                if (
                    reward is not None
                    and reward > 0
                    and baseline["baseline_tokens"]
                    and rerun_tokens
                    and rerun_tokens < baseline["baseline_tokens"]
                ):
                    bonus = min(
                        0.2,
                        0.2
                        * (
                            (baseline["baseline_tokens"] - rerun_tokens)
                            / max(1, baseline["baseline_tokens"])
                        ),
                    )
                # This exploration signal steers GEPA only. Retention below uses
                # measured reward and recorded monetary cost, not this scalar.
                score = (reward or 0.0) + bonus
                side_info.update(
                    {
                        "passed": passed,
                        "reward": reward,
                        "cost_summary": cost,
                        "tokens": rerun_tokens,
                        "tool_calls": int(rerun_summary.get("tool_calls") or 0),
                        "trajectory_summary": compact(
                            rerun_summary.get("error") or rerun_summary.get("run_dir") or "", 500
                        ),
                        "token_efficiency_bonus": round(bonus, 6),
                        "score_reason": "rerun_reward_token_score",
                    }
                )
                write_json(call_dir / "rerun_summary.json", rerun_summary)
                measured_candidates.append(outcome)
            except Exception as exc:
                score = 0.0
                side_info["score_reason"] = "rerun_exception"
                side_info["rerun_error"] = compact(str(exc), 500)
        if not cached:
            candidate_cache[candidate_key] = {
                "score": score,
                "side_info": dict(side_info),
                "rerun_info": rerun_info,
            }
        write_json(call_dir / "side_info.json", side_info)
        no_op_feedback = (
            (side_info.get("rejection_feedback_for_next_candidate") or {})
            if args.candidate_only and not diff.get("changed")
            else {}
        )
        history_row = {
            "metric_call": evaluation_counts.metric_calls,
            "candidate_id": call_dir.name,
            "real_reruns": evaluation_counts.real_reruns,
            "score": score,
            "score_type": "acceptance_gate" if args.candidate_only else "performance_reward_token",
            "candidate_path": str(call_dir / "rewritten_instruction.md"),
            "safety_status": safety["status"],
            "violations": safety["violations"],
            "decision": safety["decision"],
            "semantic_preservation_status": safety.get("semantic_preservation_status"),
            "core_task_drift": safety.get("core_task_drift", []),
            "unsupported_added_preferences": safety.get("unsupported_added_preferences", []),
            "accepted_for_rerun": bool(
                args.candidate_only and safety["status"] == "pass" and diff.get("changed")
            ),
            "rejected_for_regeneration": bool(
                args.candidate_only
                and (
                    (safety["status"] != "pass" and diff.get("changed"))
                    or (not diff.get("changed") and score < 1.0)
                )
            ),
            "side_info_path": str(call_dir / "side_info.json"),
            "rerun_dir": rerun_info["run_dir"] if rerun_info else "",
        }
        if history_row["rejected_for_regeneration"]:
            feedback = (
                dict(no_op_feedback) if no_op_feedback else rejection_feedback_from_safety(safety)
            )
            feedback.update(
                {
                    "metric_call": evaluation_counts.metric_calls,
                    "candidate_path": str(call_dir / "rewritten_instruction.md"),
                    "score_reason": side_info.get("score_reason"),
                }
            )
            rejection_feedback_memory.append(feedback)
            with (result_dir / "rejected_candidates.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(feedback, ensure_ascii=False) + "\n")
        history.append(history_row)
        with (result_dir / "metric_calls.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(history_row, ensure_ascii=False) + "\n")
        if history_row["accepted_for_rerun"]:
            with (result_dir / "accepted_candidates.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(history_row, ensure_ascii=False) + "\n")
        return score

    result = optimize_anything(
        seed_candidate=seed_instruction,
        evaluator=evaluator,
        objective=objective,
        **optimize_kwargs,
    )

    exploration_best = max(history, key=lambda row: row["score"], default=None)
    retention = None
    if not args.candidate_only:
        retention = retain_candidate(original_outcome, measured_candidates)
        best_instruction = retention.winner.instruction
        best_summary = next(
            (row for row in history if row["candidate_id"] == retention.winner.candidate_id),
            None,
        )
        write_json(
            result_dir / "retention.json",
            {
                "policy": "reward_then_recorded_cost_then_smaller_edit",
                "retained_candidate_id": retention.winner.candidate_id,
                "reason": retention.reason,
                "unresolved_cost_ties": retention.unresolved_cost_ties,
                "original_reward": original_outcome.reward,
                "original_cost": baseline_cost,
                "retained_reward": retention.winner.reward,
                "retained_cost_usd": retention.winner.cost_usd,
                "retained_cost_cny": retention.winner.cost_cny,
                "evaluated_candidates": len(measured_candidates),
                "gepa_exploration_score_used_for_retention": False,
            },
        )
    elif exploration_best and exploration_best.get("candidate_path"):
        best_summary = exploration_best
        # Keep final text, score and side_info tied to the same metric call.
        # GEPA result.best_candidate may be absent or may not correspond to
        # the max(history) row in candidate-only/offline modes.
        best_instruction = Path(best_summary["candidate_path"]).read_text(encoding="utf-8")
    else:
        best_summary = None
        # Candidate-only mode makes no performance-retention claim.
        best_instruction = extract_best_candidate(result, seed_instruction)
    final_safety = safety_gate_for_mode(
        args.adaptation_mode, original_instruction, best_instruction
    )
    write_text(result_dir / "best_rewritten_instruction.md", best_instruction)
    write_text(
        result_dir / "best_instruction.diff",
        "\n".join(
            difflib.unified_diff(
                original_instruction.splitlines(),
                best_instruction.splitlines(),
                fromfile="original/instruction.md",
                tofile="best/instruction.md",
                lineterm="",
            )
        ),
    )
    write_json(result_dir / "best_safety_gate.json", final_safety)

    run_log_path = result_dir / "gepa_engine" / "run_log.txt"
    if args.reflection_model and run_log_path.exists():
        run_log_text = run_log_path.read_text(encoding="utf-8", errors="ignore")
        reflection_auth_failure = (
            "AuthenticationError" in run_log_text
            or "The api_key client option must be set" in run_log_text
            or "missing API key" in run_log_text
        )
        if reflection_auth_failure:
            raise SystemExit(
                "reflection model proposal failed due to missing authentication; "
                "set OPENAI_API_KEY or a mapped provider key such as DASHSCOPE_API_KEY/BAILIAN_API_KEY, "
                "and ensure OPENAI_BASE_URL is set for OpenAI-compatible provider routing when needed"
            )

    optimized_passed = retention.winner.passed if retention else None
    optimized_tokens = int(baseline["baseline_tokens"] or 0) if retention else 0
    optimized_reward = retention.winner.reward if retention else None
    rewritten_instruction_path = result_dir / "best_rewritten_instruction.md"
    if best_summary:
        side_info = read_json(best_summary["side_info_path"])
        optimized_tokens = int(side_info.get("tokens") or 0)
    accepted_candidates_path = result_dir / "accepted_candidates.jsonl"
    rejected_candidates_path = result_dir / "rejected_candidates.jsonl"
    task_result = {
        "task_id": args.task_id,
        "combo": args.combo,
        "original_instruction_path": str(original_instruction_path),
        "seed_instruction_path": str(seed_instruction_path),
        "seed_differs_from_original": setup["seed_differs_from_original"],
        "feedback_result_path": str(args.baseline_result) if args.baseline_result else "",
        "previous_result_path": str(args.previous_result) if args.previous_result else "",
        "round_index": int(args.round_index or 1),
        "round_objective": round_feedback.get("round_objective"),
        "round_failure_type": round_feedback.get("failure_type"),
        "safety_reference_instruction_path": str(original_instruction_path),
        "baseline_passed": original_outcome.passed,
        "baseline_reward": original_outcome.reward,
        "optimized_passed": optimized_passed,
        "optimized_reward": optimized_reward,
        "baseline_cost": baseline_cost,
        "optimized_cost_usd": retention.winner.cost_usd if retention else None,
        "optimized_cost_cny": retention.winner.cost_cny if retention else None,
        "retention_policy": "reward_then_recorded_cost_then_smaller_edit" if retention else None,
        "retention_reason": retention.reason if retention else None,
        "retained_candidate_id": retention.winner.candidate_id if retention else None,
        "unresolved_cost_ties": retention.unresolved_cost_ties if retention else [],
        "retained_changed_instruction": bool(
            retention and retention.winner.candidate_id != "original"
        ),
        "candidate_only": bool(args.candidate_only),
        "accepted_candidate": bool(
            args.candidate_only
            and final_safety["status"] == "pass"
            and diff_summary(original_instruction, best_instruction).get("changed")
        ),
        "accepted_candidate_meaning": "candidate-only safety/diff accepted for external rerun; not an optimization-success claim"
        if args.candidate_only
        else "not_applicable",
        "accepted_candidate_is_optimization_success": False if args.candidate_only else None,
        "optimization_success_requires_external_rerun": bool(args.candidate_only),
        "accepted_candidates_path": str(accepted_candidates_path)
        if accepted_candidates_path.exists()
        else "",
        "rejected_candidates_path": str(rejected_candidates_path)
        if rejected_candidates_path.exists()
        else "",
        "rejected_candidate_count": sum(
            1 for row in history if row.get("rejected_for_regeneration")
        ),
        "best_score": best_summary["score"] if best_summary else None,
        "exploration_best_score": exploration_best["score"] if exploration_best else None,
        "exploration_best_candidate_id": exploration_best["candidate_id"]
        if exploration_best
        else None,
        "exploration_score_used_for_retention": False if retention else None,
        "score_type": "acceptance_gate" if args.candidate_only else "performance_reward_token",
        "baseline_tokens": int(baseline["baseline_tokens"] or 0),
        "baseline_efficiency_friction": efficiency_friction,
        "optimized_tokens": optimized_tokens,
        "token_delta_pct": (
            ""
            if args.candidate_only
            else round(
                ((optimized_tokens - baseline["baseline_tokens"]) / baseline["baseline_tokens"])
                * 100,
                4,
            )
            if baseline["baseline_tokens"]
            else ""
        ),
        "safety_status": final_safety["status"],
        "violations": final_safety["violations"],
        "decision": final_safety["decision"],
        "safety_reason": final_safety.get("reason", ""),
        "semantic_preservation_status": final_safety.get("semantic_preservation_status", ""),
        "core_actions_original": final_safety.get("core_actions_original", []),
        "core_actions_rewritten": final_safety.get("core_actions_rewritten", []),
        "core_task_drift": final_safety.get("core_task_drift", []),
        "unsupported_added_preferences": final_safety.get("unsupported_added_preferences", []),
        "rewritten_instruction_path": str(rewritten_instruction_path),
        "diff_path": str(result_dir / "best_instruction.diff"),
        "metric_calls": evaluation_counts.metric_calls,
        "real_reruns": evaluation_counts.real_reruns,
        "result_dir": str(result_dir),
        "runner_connected": runner_connected,
        "adaptation_mode": args.adaptation_mode,
        "gepa_module_path": gepa_info["module_path"],
        "gepa_version": gepa_info["version"],
        "gepa_api": setup["gepa_info"].get("resolved_api", {}),
    }
    write_json(result_dir / "gepa_task_result.json", task_result)
    print(json.dumps(task_result, indent=2))


if __name__ == "__main__":
    main()

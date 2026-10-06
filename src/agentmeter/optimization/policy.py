"""Rewrite objectives, baseline policies, and candidate acceptance rules."""

from __future__ import annotations

import textwrap
from typing import Any

from .safety import combo_adapted_instruction_safety_gate, instruction_safety_gate

DEFAULT_OBJECTIVE = textwrap.dedent(
    """
    Optimize the benchmark task instruction for clarity and agent token efficiency while preserving the original task exactly.

    The rewritten instruction must be semantically equivalent to the original instruction. It must keep the same task objective, input files, output files, output format, evaluation target, and difficulty.

    You may only clarify public task requirements, reorganize existing public information, make ambiguous public constraints explicit, or improve readability.

    Do not add solver strategies, algorithm hints, implementation steps, debugging advice, checker-specific information, hidden evaluator details, hidden tests, gold answers, environment fixes, dependency changes, or meta instructions such as "think step by step" or "be careful."

    The goal is not to make the task easier. The goal is to make the public task description clearer for this model+CLI combo so the agent is more likely to finish correctly with fewer steps, fewer tool calls, less repeated file inspection, less output-format hesitation, and fewer wasted tokens while keeping the benchmark interface unchanged.

    Use trajectory feedback only as evidence of where this combo previously got delayed or confused. You may turn that evidence into public task-text clarifications, but you must not mention the prior run, hidden evaluators, checker behavior, gold answers, or private tests in the rewritten instruction.

    Return the full final instruction.md text that the agent should execute directly. Do not return editing advice or meta instructions.
    """
).strip()

GENERIC_NO_TRAJECTORY_OBJECTIVE = textwrap.dedent(
    """
    Optimize the benchmark task instruction for public clarity and execution efficiency while preserving the original task exactly.

    The rewritten instruction must be semantically equivalent to the original instruction. It must keep the same task objective, input files, output files, output format, evaluation target, and difficulty.

    You may only use the original public task description itself. Do not assume access to any prior trajectory, friction diagnosis, model identity, CLI identity, execution result, hidden evaluator behavior, or benchmark-internal metadata.

    You may clarify public task requirements, reorganize existing public information, make ambiguous public constraints explicit, or improve readability. The goal is to reduce misunderstanding, output-format hesitation, repeated file inspection, and other avoidable inefficiency using only task-facing clarifications.

    Do not add solver strategies, algorithm hints, implementation steps, debugging advice, checker-specific information, hidden evaluator details, hidden tests, gold answers, environment fixes, dependency changes, or meta instructions such as "think step by step" or "be careful."

    Do not make the task easier by adding new domain heuristics, narrowing the scope, changing completion requirements, or introducing new public preferences that are not already supported by the original instruction or public artifacts.

    Return the full final instruction.md text that the agent should execute directly. Do not return editing advice or meta instructions.
    """
).strip()

COMBO_ADAPTED_OBJECTIVE = textwrap.dedent(
    """
    Optimize this benchmark task instruction specifically for the target model+CLI combo by looking for task-description adaptation issues in its previous trajectory.

    The main goal is to fix mismatches between the public task description and how this combo interpreted or executed the task. These mismatches may appear as output-format hesitation, public artifact role confusion, ambiguous completion conditions, boundary/edge-case confusion, repeated file inspection, repeated command loops, premature finalization, or other route friction.

    Reward/pass is the primary validation metric. Token/step/tool-call reduction is an important secondary metric, but only when it comes from resolving a task-description adaptation issue rather than merely shortening the instruction.

    You may use the trajectory feedback as evidence of where this combo previously misunderstood, over-inspected, delayed, or took an inefficient route. Convert that evidence into task-facing instruction improvements: clearer public file roles, explicit output contract, completion condition, edge-case handling, and concise requirement organization.

    It is acceptable if the rewritten instruction is more explicit or easier for this combo, as long as it remains a benchmark task instruction for the same task interface. Keep the same required input files, required output files, and evaluation target.

    Do not mention the previous trajectory, model, CLI, token cost, checker, hidden evaluator, hidden tests, gold answers, private tests, environment fixes, dependency changes, or instructions to inspect tests/checkers.

    Do not prescribe a full solver route or implementation algorithm unless that exact method is already part of the public task instruction. Prefer public-facing constraints and output/completion requirements over coding advice.

    For code/API tasks, clarify observable public behavior such as method semantics, return values, state transitions, edge cases, and completion conditions. Do not introduce internal data structures, concrete implementation APIs, worker/control-flow mechanisms, or debugging instructions that were not already public, such as asyncio.PriorityQueue, asyncio.create_task, OrderedDict, threading.Lock, custom test scripts, or instructions to skip running/debugging tests.

    Return the complete final instruction.md text that the agent should execute directly. Do not return edit notes, explanations, or meta instructions.
    """
).strip()

COMBO_ADAPTED_EFFICIENCY_OBJECTIVE = textwrap.dedent(
    """
    Optimize this benchmark task instruction specifically for the target model+CLI combo, but this combo already passes the task on the baseline run.

    Your goal in this case is not to reinterpret the task or improve reward by changing task semantics. Your goal is to reduce wasted tokens, unnecessary file reads, repeated command/test loops, output-format hesitation, and other route detours while preserving the task's public requirements as closely as possible.

    Prefer only low-risk public clarifications:
    - requirement ordering
    - explicit output file and output schema placement
    - completion condition
    - concise public artifact role clarification
    - stopping condition once the required outputs are produced

    Do not add new domain heuristics, category mappings, formula choices, conversion rules, analysis standards, precision escalation, or task-specific methodological preferences unless they are already explicitly present in the original public instruction.

    Keep the same required input files, required output files, public task semantics, and evaluation target. If the task already seems clear, make only a minimal rewrite or keep the instruction nearly unchanged.

    Do not mention the previous trajectory, model, CLI, token cost, checker, hidden evaluator, hidden tests, gold answers, private tests, environment fixes, dependency changes, or instructions to inspect tests/checkers.

    Return the complete final instruction.md text that the agent should execute directly. Do not return edit notes, explanations, or meta instructions.
    """
).strip()


def objective_for_mode(mode: str, *, baseline_passed: bool = False) -> str:
    if mode == "generic_no_trajectory":
        return GENERIC_NO_TRAJECTORY_OBJECTIVE
    if mode != "combo_adapted":
        return DEFAULT_OBJECTIVE
    if baseline_passed:
        return COMBO_ADAPTED_EFFICIENCY_OBJECTIVE
    return COMBO_ADAPTED_OBJECTIVE


def adaptation_policy_for_baseline(baseline: dict[str, Any], mode: str) -> dict[str, Any]:
    trajectory_evidence = baseline.get("trajectory_evidence") or {}
    baseline_passed = bool(baseline.get("baseline_passed"))
    if mode == "generic_no_trajectory":
        return {
            "policy": "public-only generic rewrite: preserve original task semantics while clarifying the public instruction without any trajectory or identity-specific feedback",
            "optimization_target": "preserve task semantics while improving public clarity using only the original instruction text",
            "adaptation_goal": "Use only the original public instruction to remove ambiguity, clarify artifact roles, clarify output/completion requirements, and improve readability without changing the task interface.",
            "agent_efficiency_goal": "Any efficiency gain must come from public-facing clarification alone, not from model-specific, CLI-specific, or trajectory-specific hints.",
            "trajectory_rewrite_guidance": [],
            "baseline_mode": "generic_public_only",
            "uses_trajectory_feedback": False,
        }
    if mode != "combo_adapted":
        return {
            "policy": "preserve original task objective, inputs, outputs, difficulty, and hidden evaluator boundary",
            "optimization_target": "preserve task semantics while clarifying public requirements",
            "adaptation_goal": trajectory_evidence.get("adaptation_goal", ""),
            "agent_efficiency_goal": trajectory_evidence.get("agent_efficiency_goal", ""),
            "trajectory_rewrite_guidance": trajectory_evidence.get("rewrite_guidance", []),
            "baseline_mode": "strict",
            "uses_trajectory_feedback": True,
        }
    if baseline_passed:
        return {
            "policy": "combo-specific efficiency adaptation only: preserve public task semantics and use the prior successful trajectory only to remove detours, repeated inspection, and output/completion hesitation",
            "optimization_target": "primary=lower tokens/steps/tool calls without reducing reward; do not change task semantics, analysis standards, or public requirement meaning",
            "adaptation_goal": "This combo already passes the task. Rewrite only to reduce route friction and token waste while preserving the original public task meaning as closely as possible.",
            "agent_efficiency_goal": "Prefer minimal public clarifications that reduce repeated reads, command loops, output-format hesitation, and delayed stopping. Do not add new task semantics, domain heuristics, category mappings, formulas, conversion rules, or precision requirements.",
            "trajectory_rewrite_guidance": [
                "Keep the rewrite minimal and task-facing. Reorder or foreground existing public requirements instead of adding new semantic constraints.",
                "If helpful, surface the required output file, output schema, and completion condition earlier so the agent can stop once the required outputs are produced.",
                "Reduce repeated artifact inspection and validation loops by clarifying public file roles and final deliverable expectations only.",
                "Do not add new domain heuristics, category mappings, formulas, conversion rules, or precision escalation unless already explicit in the original instruction.",
            ],
            "baseline_mode": "passed_efficiency_only",
            "uses_trajectory_feedback": True,
        }
    return {
        "policy": "combo-specific task-description adaptation: use prior trajectory friction to identify and repair mismatches between public task wording and this combo's route, while preserving public I/O and evaluator boundary",
        "optimization_target": "primary=find and fix task-description adaptation issues that improve pass/reward; secondary=lower tokens/steps/tool calls when caused by reduced route friction",
        "adaptation_goal": trajectory_evidence.get("adaptation_goal", ""),
        "agent_efficiency_goal": trajectory_evidence.get("agent_efficiency_goal", ""),
        "trajectory_rewrite_guidance": trajectory_evidence.get("rewrite_guidance", []),
        "baseline_mode": "failed_or_partial",
        "uses_trajectory_feedback": True,
    }


def safety_gate_for_mode(mode: str, original: str, rewritten: str) -> dict[str, Any]:
    if mode == "combo_adapted":
        return combo_adapted_instruction_safety_gate(original, rewritten)
    return instruction_safety_gate(original, rewritten)


def candidate_only_acceptance_score(
    diff: dict[str, Any], safety: dict[str, Any]
) -> tuple[float, str]:
    """Offline first-stage acceptance score.

    Candidate-only mode is not a performance estimate. It only separates
    unsafe/unchanged candidates from accepted rewritten instructions. Reward
    and token efficiency are measured in the manual second-stage rerun.
    """
    if safety.get("status") == "fail":
        return 0.0, "candidate_only_rejected_safety_fail"
    if safety.get("status") == "needs_manual_review":
        return 0.0, "candidate_only_rejected_needs_manual_review"
    if not diff.get("changed"):
        return 0.0, "candidate_only_unchanged"
    return 1.0, "candidate_only_accepted_safe_rewrite"


def baseline_efficiency_friction(baseline: dict[str, Any]) -> dict[str, Any]:
    """Decide whether a passing baseline should still explore efficiency rewrites.

    This is intentionally task-agnostic: it looks only at route cost and detour
    signals, not task ids or domain-specific fields.
    """
    evidence = (
        baseline.get("trajectory_evidence")
        if isinstance(baseline.get("trajectory_evidence"), dict)
        else {}
    )
    profile = (
        evidence.get("route_profile") if isinstance(evidence.get("route_profile"), dict) else {}
    )
    repeated_reads = (
        profile.get("repeated_reads") if isinstance(profile.get("repeated_reads"), list) else []
    )
    repeated_commands = (
        profile.get("repeated_commands")
        if isinstance(profile.get("repeated_commands"), list)
        else []
    )
    high_token_events = (
        profile.get("high_token_events")
        if isinstance(profile.get("high_token_events"), list)
        else []
    )
    rewrite_guidance = (
        evidence.get("rewrite_guidance")
        if isinstance(evidence.get("rewrite_guidance"), list)
        else []
    )
    friction_signals = (
        evidence.get("friction_signals")
        if isinstance(evidence.get("friction_signals"), list)
        else []
    )

    tokens = int(baseline.get("baseline_tokens") or 0)
    turns = int(
        baseline.get("baseline_turns") or profile.get("total_steps") or profile.get("steps") or 0
    )
    tool_calls = int(baseline.get("baseline_tool_calls") or 0)
    reasons: list[str] = []
    if tokens >= 200_000:
        reasons.append("high_total_tokens")
    if turns >= 20:
        reasons.append("long_route_steps")
    if tool_calls >= 30:
        reasons.append("high_tool_calls")
    if repeated_reads:
        reasons.append("repeated_file_reads")
    if repeated_commands:
        reasons.append("repeated_commands")
    if high_token_events:
        reasons.append("high_token_steps")
    if len(friction_signals) >= 6 and rewrite_guidance:
        reasons.append("multiple_route_friction_signals")
    return {
        "has_efficiency_friction": bool(reasons),
        "reasons": reasons,
        "tokens": tokens,
        "turns": turns,
        "tool_calls": tool_calls,
        "repeated_reads_count": len(repeated_reads),
        "repeated_commands_count": len(repeated_commands),
        "high_token_events_count": len(high_token_events),
    }


def rejection_feedback_from_safety(safety: dict[str, Any]) -> dict[str, Any]:
    violations = list(safety.get("violations") or [])
    guidance: list[str] = []
    if "implementation_route" in violations or "solver_hint" in violations:
        guidance.append(
            "Regenerate without implementation-route content. Clarify public behavior only: method semantics, return values, state transitions, edge cases, output/completion conditions. Do not add internal data structures, concrete library APIs, worker/control-flow mechanisms, algorithm choices, custom test scripts, or debugging instructions."
        )
    if "hidden_evaluator" in violations:
        guidance.append(
            "Remove any reference to hidden evaluators, tests, checker/scoring scripts, oracle solutions, rewards, or private evaluation behavior."
        )
    if "environment_fix" in violations:
        guidance.append(
            "Remove environment, dependency, runner, package-install, test-patching, or checker-editing instructions."
        )
    if "changed_public_io_interface" in violations:
        guidance.append(
            "Preserve the public input/output interface exactly: required files, output path, column names, JSON keys, value container types, and declared output format."
        )
    if (
        "dropped_key_public_requirements" in violations
        or "missing_original_public_paths" in violations
    ):
        guidance.append(
            "Keep all original public requirements and public paths. You may reorganize or clarify them, but do not remove required methods, files, outputs, schemas, or constraints."
        )
    if "changed_core_task_objective" in violations:
        guidance.append(
            "Preserve every original core task action and objective. Do not collapse multi-part objectives into a smaller task; for example, if the original asks to identify and count, the rewrite must still ask for both."
        )
    if "unsupported_public_preference_addition" in violations:
        guidance.append(
            "Remove newly added ordering, rounding, exhaustive-enumeration, schema, or formatting preferences unless they are explicitly anchored in the original public instruction or public sample artifact. Rephrase only as public artifact-following requirements when the anchor is clear."
        )
    if "difficulty_reduction" in violations:
        guidance.append(
            "Do not reduce the task scope, skip work, tell the agent it need not run/debug, ignore cases, or narrow the required input/output behavior."
        )
    if not guidance:
        guidance.append(
            "Regenerate a bounded task-facing rewrite that preserves public I/O and avoids hidden information, solver hints, environment changes, and task-scope reduction."
        )
    return {
        "violations": violations,
        "safety_status": safety.get("status"),
        "safety_reason": safety.get("reason"),
        "semantic_preservation_status": safety.get("semantic_preservation_status"),
        "core_actions_original": safety.get("core_actions_original", []),
        "core_actions_rewritten": safety.get("core_actions_rewritten", []),
        "core_task_drift": safety.get("core_task_drift", []),
        "unsupported_added_preferences": safety.get("unsupported_added_preferences", []),
        "regeneration_guidance": guidance,
    }

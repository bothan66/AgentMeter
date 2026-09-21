#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import importlib
import importlib.metadata
import inspect
import json
import os
import shutil
import sys
import textwrap
import tomllib
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from agentmeter_harness import Experiment, TaskSpec, api_lookup, load_api_configs, read_json, run_attempt, write_json  # type: ignore
from agentmeter_opt.safety_gate import combo_adapted_instruction_safety_gate, instruction_safety_gate


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

DEFAULT_RUNNER_CONFIGS = [
    ROOT / "configs" / "runners.local.yaml",
    ROOT / "configs" / "runners" / "runners.local.yaml",
]
COMBO_ALIASES = {
    "qwen36_kimi_cli": ("Qwen3.6+", "kimi-cli"),
    "qwen36_qwen_coder": ("Qwen3.6+", "qwen-coder"),
    "qwen36_codex": ("Qwen3.6+", "codex"),
    "glm51_qwen_coder": ("GLM-5.1", "qwen-coder"),
    "glm51_qwencoder": ("GLM-5.1", "qwen-coder"),
}
FILE_OR_PATH_RE = re.compile(r"/|[\w+-]+\.(?:csv|json|txt|md|py|sh|yaml|yml|toml|pdf|tsv)$", re.I)
PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)
REFLECTION_API_KEY_ENVS = (
    "OPENAI_API_KEY",
    "DASHSCOPE_API_KEY",
    "ALIBABA_CLOUD_API_KEY",
    "BAILIAN_API_KEY",
    "AGENTMETER_API_KEY",
)
DEFAULT_REFLECTION_OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_") or "item"


def compact(text: Any, limit: int = 600) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 16)].rstrip() + " ... [truncated]"


def discover_runner_config(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit if explicit.exists() else None
    for path in DEFAULT_RUNNER_CONFIGS:
        if path.exists():
            return path
    return None


def parse_combo(combo: str, model: str | None, cli: str | None) -> tuple[str, str]:
    if model and cli:
        return model, cli
    if "__" in combo:
        left, right = combo.split("__", 1)
        return model or left, cli or right
    if combo in COMBO_ALIASES:
        left, right = COMBO_ALIASES[combo]
        return model or left, cli or right
    if model and not cli:
        return model, combo
    raise SystemExit(f"cannot infer model/cli from combo={combo!r}; pass --model and --cli explicitly")


def detect_gepa() -> dict[str, Any]:
    info: dict[str, Any] = {
        "installed": False,
        "module_path": "",
        "version": "",
        "api": {},
        "error": "",
    }
    try:
        gepa = importlib.import_module("gepa")
        oa = importlib.import_module("gepa.optimize_anything")
    except Exception as exc:
        info["error"] = str(exc)
        return info
    info["installed"] = True
    info["module_path"] = str(getattr(gepa, "__file__", ""))
    try:
        info["version"] = importlib.metadata.version("gepa")
    except Exception:
        info["version"] = ""
    info["api"] = {
        "optimize_anything_module": str(getattr(oa, "__file__", "")),
        "optimize_anything_signature": str(inspect.signature(getattr(oa, "optimize_anything"))),
        "has_GEPAConfig": hasattr(oa, "GEPAConfig"),
        "has_EngineConfig": hasattr(oa, "EngineConfig"),
        "has_log": hasattr(oa, "log"),
    }
    return info


def runner_has_route(runner_config: Path | None, model: str, cli: str) -> bool:
    if not runner_config:
        return False
    try:
        api_lookup(load_api_configs(runner_config), model, cli)
        return True
    except Exception:
        return False


def extract_paths(text: str) -> set[str]:
    matches = re.findall(r"`([^`]+)`|(/[\w./+-]+)|\b([\w./+-]+\.(?:csv|json|txt|md|py|sh|yaml|yml|toml|pdf|tsv))\b", text)
    out: set[str] = set()
    for groups in matches:
        code_span, abs_path, file_name = groups
        if code_span and FILE_OR_PATH_RE.search(code_span):
            out.add(code_span.strip("`"))
        if abs_path:
            out.add(abs_path.strip("`"))
        if file_name:
            out.add(file_name.strip("`"))
    return out


def is_public_path_composition(path: str, original_paths: set[str]) -> bool:
    if "/" not in path:
        return False
    pieces = path.rstrip("/").rsplit("/", 1)
    if len(pieces) != 2:
        return False
    parent, name = pieces
    return name in original_paths and (parent in original_paths or parent + "/" in original_paths)


def diff_summary(original: str, rewritten: str) -> dict[str, Any]:
    original_lines = original.splitlines()
    rewritten_lines = rewritten.splitlines()
    diff = list(difflib.unified_diff(original_lines, rewritten_lines, fromfile="original/instruction.md", tofile="rewritten/instruction.md", lineterm=""))
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    return {
        "changed": " ".join(original.split()) != " ".join(rewritten.split()),
        "added_lines": added,
        "removed_lines": removed,
        "original_paths": sorted(extract_paths(original)),
        "rewritten_paths": sorted(extract_paths(rewritten)),
        "new_paths": sorted(
            path for path in extract_paths(rewritten)
            if path not in extract_paths(original) and not is_public_path_composition(path, extract_paths(original))
        ),
    }


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


def clear_proxy_environment() -> dict[str, str]:
    removed: dict[str, str] = {}
    for key in PROXY_ENV_KEYS:
        value = os.environ.pop(key, None)
        if value:
            removed[key] = value
    os.environ.setdefault("NO_PROXY", "*")
    os.environ.setdefault("no_proxy", "*")
    return removed


def configure_reflection_provider_environment(reflection_model: str | None) -> dict[str, Any]:
    """Map local provider envs into the OpenAI-compatible vars GEPA/LiteLLM expects."""
    info = {
        "reflection_model": reflection_model or "",
        "mapped_api_key_env": "",
        "base_url": "",
        "source_envs_present": [key for key in REFLECTION_API_KEY_ENVS if os.environ.get(key)],
    }
    if not reflection_model:
        return info
    model_lower = reflection_model.lower()
    if not (model_lower.startswith("openai/") or model_lower.startswith("openai:")):
        return info
    if not os.environ.get("OPENAI_API_KEY"):
        for key in REFLECTION_API_KEY_ENVS:
            value = os.environ.get(key)
            if value:
                os.environ["OPENAI_API_KEY"] = value
                info["mapped_api_key_env"] = key
                break
    else:
        info["mapped_api_key_env"] = "OPENAI_API_KEY"
    if not os.environ.get("OPENAI_BASE_URL") and info["mapped_api_key_env"] in {"DASHSCOPE_API_KEY", "ALIBABA_CLOUD_API_KEY", "BAILIAN_API_KEY", "AGENTMETER_API_KEY"}:
        os.environ["OPENAI_BASE_URL"] = DEFAULT_REFLECTION_OPENAI_BASE_URL
        info["base_url"] = DEFAULT_REFLECTION_OPENAI_BASE_URL
    elif os.environ.get("OPENAI_BASE_URL"):
        info["base_url"] = str(os.environ.get("OPENAI_BASE_URL") or "")
    return info


def _tool_name(call: dict[str, Any]) -> str:
    return str(call.get("function_name") or call.get("name") or call.get("tool") or "")


def _tool_target(call: dict[str, Any]) -> str:
    raw_args = call.get("arguments")
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            args = parsed if isinstance(parsed, dict) else {"raw": raw_args}
        except Exception:
            args = {"raw": raw_args}
    else:
        args = raw_args if isinstance(raw_args, dict) else {}
    for key in ("path", "command", "cmd", "file"):
        if args.get(key):
            return compact(args.get(key), 180)
    raw = args.get("raw")
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith("{") or stripped.endswith(":"):
            return ""
        return compact(stripped, 180)
    return ""


def _obs_text(step: dict[str, Any]) -> str:
    obs = step.get("observation")
    if isinstance(obs, dict):
        chunks = []
        for item in obs.get("results") or []:
            if isinstance(item, dict):
                chunks.append(str(item.get("content") or item.get("text") or ""))
        if chunks:
            return "\n".join(chunks)
    return str(obs or "")


def _step_id(step: dict[str, Any], idx: int) -> str:
    return str(step.get("step_id") or step.get("turn") or idx + 1)


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(item in lowered for item in needles)


def _evidence_priority(row: dict[str, Any]) -> int:
    tags = set(row.get("route_tags") or [])
    score = 0
    if "outcome_contradiction" in tags:
        score += 8
    if "code_or_interface_boundary" in tags:
        score += 7
    if "route_decision" in tags:
        score += 6
    if "error_or_feedback" in tags:
        score += 6
    if "output_or_artifact" in tags:
        score += 5
    if "inspection_or_format_understanding" in tags:
        score += 4
    if "high_token_step" in tags:
        score += 4
    if "command_or_test" in tags:
        score += 3
    if row.get("tool_calls"):
        score += 1
    return score


def _tokens_for_overlap(text: str) -> set[str]:
    return {
        tok.lower()
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}|/[A-Za-z0-9_./+-]+|[A-Za-z0-9_.+-]+\.(?:csv|json|txt|md|py|tsv|xlsx|pdf)", text or "")
        if len(tok) >= 3
    }


def extract_public_anchors(public_instruction: str, *, max_anchors: int = 12) -> list[dict[str, Any]]:
    """Extract task-facing anchors without using task ids or hidden files."""
    anchors: list[dict[str, Any]] = []
    seen: set[str] = set()
    lines = public_instruction.splitlines()
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"`{3,}\w*", line) or re.fullmatch(r"`{3,}", line):
            continue
        if re.fullmatch(r"#{1,6}\s+.+", line):
            continue
        if re.fullmatch(r"[-*]\s*$", line):
            continue
        lowered = line.lower()
        has_code_or_path = "`" in line or "/" in line or re.search(r"\b\w+\.(?:csv|json|txt|md|py|tsv|xlsx|pdf)\b", line, flags=re.I)
        has_interface = bool(re.search(r"\b(class|def|function|method|return|returns|write|save|output|input|format|schema|must|exactly|if|when|otherwise|edge|expired|priority|fifo|thread-safe|concurrent)\b", lowered))
        has_signature = bool(re.search(r"\b(?:class|def)\s+[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*\([^)]*\)\s*(?:->\s*[^`]+)?", line))
        if not (has_code_or_path or has_interface or has_signature):
            continue
        if line in seen:
            continue
        seen.add(line)
        if has_signature:
            kind = "public_interface_signature"
        elif has_code_or_path:
            kind = "public_file_or_output_contract"
        elif re.search(r"\b(if|when|otherwise|expired|priority|fifo|concurrent|thread-safe|must|exactly)\b", lowered):
            kind = "public_boundary_condition"
        else:
            kind = "public_requirement"
        anchors.append({
            "anchor_id": f"anchor_{len(anchors) + 1:02d}",
            "line_no": idx + 1,
            "anchor_type": kind,
            "text": compact(line, 360),
            "tokens": sorted(_tokens_for_overlap(line))[:30],
        })
        if len(anchors) >= max_anchors:
            break
    return anchors


def _route_decision_kind(text: str, tools: list[dict[str, Any]]) -> str:
    lowered = text.lower()
    if re.search(r"\b(schema|format|column|header|json|csv|output path|result file|sample)\b", lowered):
        return "output_contract_choice"
    if re.search(r"\b(edge case|expired|ttl|lru|priority|fifo|concurrent|thread|return none|exception|boundary)\b", lowered):
        return "public_interface_boundary_choice"
    if re.search(r"\b(model|cluster|classifier|regression|feature|metric|parameter|threshold|validate)\b", lowered):
        return "modeling_or_metric_choice"
    if re.search(r"\b(try|instead|switch|alternative|fallback|retry|rerun|debug|fix)\b", lowered):
        return "repair_or_strategy_switch"
    if any(re.search(r"\b(pytest|test|python|bash|harbor)\b", str(item.get("target") or ""), flags=re.I) for item in tools):
        return "validation_or_command_choice"
    if tools:
        return "tool_use_choice"
    return "interpretation_choice"


def _match_public_anchors(text: str, anchors: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    text_tokens = _tokens_for_overlap(text)
    matches: list[tuple[int, dict[str, Any]]] = []
    for anchor in anchors:
        anchor_tokens = set(anchor.get("tokens") or [])
        if not anchor_tokens:
            continue
        overlap = len(text_tokens & anchor_tokens)
        if overlap:
            matches.append((overlap, anchor))
    matches.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "anchor_id": anchor["anchor_id"],
            "anchor_type": anchor["anchor_type"],
            "overlap": overlap,
            "text": anchor["text"],
        }
        for overlap, anchor in matches[:limit]
    ]


def build_trajectory_evidence(path: Path | None, *, public_instruction: str = "", max_events: int = 8) -> dict[str, Any]:
    """Compact a prior agent trajectory into GEPA side_info.

    This is retrieval, not diagnosis: it preserves route evidence so GEPA's
    official reflective proposer can decide how to rewrite the instruction.
    """
    empty = {
        "available": False,
        "source_path": str(path) if path else "",
        "route_profile": {},
        "public_anchors": extract_public_anchors(public_instruction),
        "route_evidence": [],
        "route_decision_points": [],
        "evidence_chains": [],
        "friction_signals": [],
        "adaptation_goal": "Find task-description adaptation issues exposed by this combo's trajectory, then rewrite the public instruction so the combo is less likely to misunderstand the task, miss the output contract, over-inspect artifacts, loop on commands, or waste tokens.",
        "agent_efficiency_goal": "Token reduction is a secondary benefit: prefer rewrites that reduce unnecessary reads, repeated commands, output-format hesitation, and token-heavy detours by fixing task-description adaptation issues.",
        "rewrite_guidance": [],
    }
    if not path or not path.exists() or path.suffix.lower() != ".json":
        return empty
    try:
        data = read_json(path)
    except Exception as exc:
        out = dict(empty)
        out["load_error"] = compact(str(exc), 300)
        return out
    steps = data.get("steps") if isinstance(data.get("steps"), list) else []
    final_metrics = data.get("final_metrics") if isinstance(data.get("final_metrics"), dict) else {}
    route_evidence: list[dict[str, Any]] = []
    public_anchors = extract_public_anchors(public_instruction)
    route_decision_points: list[dict[str, Any]] = []
    friction_signals: list[dict[str, Any]] = []
    read_targets: dict[str, int] = {}
    command_targets: dict[str, int] = {}

    for idx, step in enumerate(steps):
        tool_calls = step.get("tool_calls") if isinstance(step.get("tool_calls"), list) else []
        tools = []
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            name = _tool_name(call)
            target = _tool_target(call)
            if target:
                tools.append({"tool": name, "target": target})
            lname = name.lower()
            if "read" in lname and target:
                read_targets[target] = read_targets.get(target, 0) + 1
            if ("shell" in lname or "command" in lname) and target:
                command_targets[target] = command_targets.get(target, 0) + 1
        metrics = step.get("metrics") if isinstance(step.get("metrics"), dict) else {}
        token_total = int(metrics.get("prompt_tokens") or 0) + int(metrics.get("completion_tokens") or 0) + int(metrics.get("cached_tokens") or 0)
        obs = _obs_text(step)
        raw_text_blob = " ".join([
            str(step.get("message") or ""),
            str(step.get("reasoning_content") or ""),
            obs,
        ])
        text_blob = raw_text_blob.lower()
        tags = []
        if _contains_any(text_blob, ("error", "traceback", "permission denied", "failed", "exception")):
            tags.append("error_or_feedback")
        matched_anchors = _match_public_anchors(raw_text_blob, public_anchors)
        obs_lower = obs.lower()
        if re.search(r"\b(assert|expected|actual|mismatch|not equal|wrong|test failed|failure|failed)\b", obs_lower) or re.search(r"\b(expected|actual|mismatch|not equal|wrong|test failed)\b", text_blob):
            tags.append("outcome_contradiction")
        if _contains_any(text_blob, ("saved", "output", "result", "csv", "json", "xlsx", "pdf")):
            tags.append("output_or_artifact")
        if _contains_any(text_blob, ("read", "understand", "structure", "format", "schema", "sample", "instruction")):
            tags.append("inspection_or_format_understanding")
        if (
            any(anchor.get("anchor_type") in {"public_interface_signature", "public_boundary_condition"} for anchor in matched_anchors)
            or re.search(r"\b(class|def|method|return|returns|exception|schema|column|header|field|format)\b", text_blob)
        ):
            tags.append("code_or_interface_boundary")
        if re.search(r"\b(i will|i need|we need|should|probably|maybe|assume|decide|try|instead|switch|fallback|looks like|seems)\b", text_blob):
            tags.append("route_decision")
        if tools:
            tags.append("tool_use")
        if any(_contains_any(str(item.get("target") or ""), ("pytest", "test", "python", "bash", "harbor")) for item in tools):
            tags.append("command_or_test")
        if token_total >= 25000:
            tags.append("high_token_step")
        row = {
            "event_id": f"step_{idx + 1:03d}",
            "step_id": _step_id(step, idx),
            "message": compact(step.get("message"), 450),
            "agent_reasoning": compact(step.get("reasoning_content"), 900),
            "tool_calls": tools[:8],
            "observation_snippet": compact(obs, 700),
            "matched_public_anchors": matched_anchors,
            "metrics": {
                "prompt_tokens": metrics.get("prompt_tokens"),
                "completion_tokens": metrics.get("completion_tokens"),
                "cached_tokens": metrics.get("cached_tokens"),
                "step_tokens": token_total,
            },
            "route_tags": tags,
        }
        route_evidence.append(row)
        if "route_decision" in tags or "code_or_interface_boundary" in tags or "output_or_artifact" in tags:
            route_decision_points.append({
                "decision_id": f"decision_{len(route_decision_points) + 1:03d}",
                "event_id": row["event_id"],
                "decision_kind": _route_decision_kind(raw_text_blob, tools),
                "summary": compact(step.get("reasoning_content") or step.get("message") or obs, 360),
                "public_basis": matched_anchors[:2],
                "uncertainty_or_hesitation": bool(re.search(r"\b(probably|maybe|assume|seems|looks like|try|instead|fallback|not sure)\b", text_blob)),
                "downstream_signal": [tag for tag in tags if tag in {"error_or_feedback", "outcome_contradiction", "high_token_step", "output_or_artifact"}],
            })
        if tags:
            friction_signals.append({
                "event_id": f"step_{idx + 1:03d}",
                "signals": tags,
                "reason": compact(step.get("reasoning_content") or step.get("message"), 320),
            })

    for target, count in sorted(read_targets.items()):
        if count >= 2:
            friction_signals.append({"event_id": "aggregate", "signals": ["repeated_file_read"], "target": target, "count": count})
    for target, count in sorted(command_targets.items()):
        if count >= 2:
            friction_signals.append({"event_id": "aggregate", "signals": ["repeated_command"], "target": target, "count": count})

    if route_evidence:
        first = route_evidence[:2]
        last = route_evidence[-2:] if len(route_evidence) > 2 else []
        middle = sorted(route_evidence[2:-2], key=_evidence_priority, reverse=True)
        important = []
        seen: set[str] = set()
        for row in first + middle + last:
            if row["event_id"] not in seen:
                important.append(row)
                seen.add(row["event_id"])
            if len(important) >= max_events:
                break
        important.sort(key=lambda row: int(str(row["event_id"]).split("_")[-1]))
    else:
        important = []
    repeated_reads = [{"target": target, "count": count} for target, count in sorted(read_targets.items()) if count >= 2]
    repeated_commands = [{"target": target, "count": count} for target, count in sorted(command_targets.items()) if count >= 2]
    high_token_events = [
        {"event_id": row["event_id"], "step_tokens": row["metrics"]["step_tokens"]}
        for row in route_evidence
        if "high_token_step" in row["route_tags"]
    ][:5]
    evidence_chains: list[dict[str, Any]] = []
    for decision in route_decision_points:
        event_id = decision["event_id"]
        try:
            event_num = int(event_id.split("_")[-1])
        except Exception:
            event_num = 0
        current = next((row for row in route_evidence if row["event_id"] == event_id), None)
        if not current:
            continue
        outcomes = [
            row for row in route_evidence
            if int(row["event_id"].split("_")[-1]) >= event_num
            and ({"error_or_feedback", "outcome_contradiction", "output_or_artifact", "high_token_step"} & set(row.get("route_tags") or []))
        ][:2]
        if not outcomes and (decision.get("downstream_signal") or current.get("tool_calls")):
            outcomes = [current]
        if not decision.get("public_basis") and not outcomes:
            continue
        evidence_chains.append({
            "chain_id": f"chain_{len(evidence_chains) + 1:03d}",
            "public_anchor": decision.get("public_basis", [])[:2],
            "model_interpretation_evidence": {
                "event_id": event_id,
                "decision_kind": decision["decision_kind"],
                "summary": decision["summary"],
                "uncertainty_or_hesitation": decision["uncertainty_or_hesitation"],
            },
            "action_evidence": {
                "event_id": event_id,
                "tool_calls": current.get("tool_calls", [])[:4],
            },
            "outcome_evidence": [
                {
                    "event_id": row["event_id"],
                    "route_tags": row.get("route_tags", []),
                    "observation_snippet": row.get("observation_snippet", ""),
                    "step_tokens": (row.get("metrics") or {}).get("step_tokens"),
                }
                for row in outcomes
            ],
        })
        if len(evidence_chains) >= max(3, max_events // 2):
            break
    rewrite_guidance = []
    if repeated_reads:
        rewrite_guidance.append("If public task text/artifacts allow it, consolidate input/output locations and file roles so the agent does not repeatedly inspect the same files.")
    if repeated_commands:
        rewrite_guidance.append("If public requirements allow it, make completion/output conditions explicit so the agent can avoid repeated command/test loops.")
    if any("output_or_artifact" in row["route_tags"] for row in route_evidence):
        rewrite_guidance.append("If public output contract is present, state the required output file, schema, ordering, and artifact role directly in final instruction text.")
    if any("code_or_interface_boundary" in row["route_tags"] for row in route_evidence):
        rewrite_guidance.append("For code/API tasks, clarify public interface semantics, return values, boundary conditions, and completion behavior when the trajectory shows implementation or test-feedback confusion.")
    if any("outcome_contradiction" in row["route_tags"] for row in route_evidence):
        rewrite_guidance.append("When public anchors and outcome contradictions align, prefer bounded clarifications of the public requirement instead of adding solver strategy or hidden test details.")
    if high_token_events:
        rewrite_guidance.append("Prefer concise public clarifications that reduce long reasoning or route detours; do not add solver strategy.")
    return {
        "available": True,
        "source_path": str(path),
        "route_profile": {
            "steps": len(steps),
            "total_prompt_tokens": final_metrics.get("total_prompt_tokens"),
            "total_completion_tokens": final_metrics.get("total_completion_tokens"),
            "total_cached_tokens": final_metrics.get("total_cached_tokens"),
            "total_steps": final_metrics.get("total_steps") or len(steps),
            "read_targets": read_targets,
            "command_targets": command_targets,
            "repeated_reads": repeated_reads,
            "repeated_commands": repeated_commands,
            "high_token_events": high_token_events,
        },
        "public_anchors": public_anchors,
        "route_evidence": important[:max_events],
        "route_decision_points": route_decision_points[:max_events],
        "evidence_chains": evidence_chains,
        "friction_signals": friction_signals[: max_events + 4],
        "adaptation_goal": empty["adaptation_goal"],
        "agent_efficiency_goal": empty["agent_efficiency_goal"],
        "rewrite_guidance": rewrite_guidance,
    }


def build_public_only_evidence(public_instruction: str) -> dict[str, Any]:
    return {
        "available": False,
        "source_path": "",
        "route_profile": {},
        "public_anchors": extract_public_anchors(public_instruction),
        "route_evidence": [],
        "route_decision_points": [],
        "evidence_chains": [],
        "friction_signals": [],
        "adaptation_goal": "Use only the original public instruction to identify clarifications that reduce ambiguity, make output/completion requirements explicit, and improve readability without changing task semantics.",
        "agent_efficiency_goal": "Any efficiency improvement must come from public-facing clarification alone, not from trajectory feedback, model-specific hints, CLI-specific hints, or hidden evaluation knowledge.",
        "rewrite_guidance": [],
    }


def candidate_only_acceptance_score(diff: dict[str, Any], safety: dict[str, Any]) -> tuple[float, str]:
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
    evidence = baseline.get("trajectory_evidence") if isinstance(baseline.get("trajectory_evidence"), dict) else {}
    profile = evidence.get("route_profile") if isinstance(evidence.get("route_profile"), dict) else {}
    repeated_reads = profile.get("repeated_reads") if isinstance(profile.get("repeated_reads"), list) else []
    repeated_commands = profile.get("repeated_commands") if isinstance(profile.get("repeated_commands"), list) else []
    high_token_events = profile.get("high_token_events") if isinstance(profile.get("high_token_events"), list) else []
    rewrite_guidance = evidence.get("rewrite_guidance") if isinstance(evidence.get("rewrite_guidance"), list) else []
    friction_signals = evidence.get("friction_signals") if isinstance(evidence.get("friction_signals"), list) else []

    tokens = int(baseline.get("baseline_tokens") or 0)
    turns = int(baseline.get("baseline_turns") or profile.get("total_steps") or profile.get("steps") or 0)
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
        guidance.append("Remove any reference to hidden evaluators, tests, checker/scoring scripts, oracle solutions, rewards, or private evaluation behavior.")
    if "environment_fix" in violations:
        guidance.append("Remove environment, dependency, runner, package-install, test-patching, or checker-editing instructions.")
    if "changed_public_io_interface" in violations:
        guidance.append("Preserve the public input/output interface exactly: required files, output path, column names, JSON keys, value container types, and declared output format.")
    if "dropped_key_public_requirements" in violations or "missing_original_public_paths" in violations:
        guidance.append("Keep all original public requirements and public paths. You may reorganize or clarify them, but do not remove required methods, files, outputs, schemas, or constraints.")
    if "changed_core_task_objective" in violations:
        guidance.append(
            "Preserve every original core task action and objective. Do not collapse multi-part objectives into a smaller task; for example, if the original asks to identify and count, the rewrite must still ask for both."
        )
    if "unsupported_public_preference_addition" in violations:
        guidance.append(
            "Remove newly added ordering, rounding, exhaustive-enumeration, schema, or formatting preferences unless they are explicitly anchored in the original public instruction or public sample artifact. Rephrase only as public artifact-following requirements when the anchor is clear."
        )
    if "difficulty_reduction" in violations:
        guidance.append("Do not reduce the task scope, skip work, tell the agent it need not run/debug, ignore cases, or narrow the required input/output behavior.")
    if not guidance:
        guidance.append("Regenerate a bounded task-facing rewrite that preserves public I/O and avoids hidden information, solver hints, environment changes, and task-scope reduction.")
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


def load_task_spec(task_root: Path, task_id: str, eval_command: str, default_timeout_sec: int) -> TaskSpec:
    task_dir = task_root / task_id
    if not (task_dir / "instruction.md").exists():
        raise SystemExit(f"task instruction not found: {task_dir / 'instruction.md'}")
    toml_path = task_dir / "task.toml"
    data = tomllib.loads(toml_path.read_text(encoding="utf-8")) if toml_path.exists() else {}
    metadata = data.get("metadata") or {}
    verifier = data.get("verifier") or {}
    tags = metadata.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    timeout_sec = int(verifier.get("timeout_sec") or default_timeout_sec)
    return TaskSpec(
        task_id=task_id,
        suite="custom",
        relative_task_path=task_id,
        difficulty=str(metadata.get("difficulty") or "unknown"),
        domain=str(metadata.get("category") or "unknown"),
        tags=tuple(str(tag) for tag in tags),
        eval_type="harbor",
        eval_command=eval_command,
        timeout_sec=timeout_sec,
    )


def load_baseline_result(path: Path | None, task_id: str, combo: str) -> dict[str, Any]:
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
        final_metrics = data.get("final_metrics") if isinstance(data.get("final_metrics"), dict) else {}
        total_tokens = (
            data.get("total_tokens")
            or data.get("tokens")
            or ((data.get("agent_result") or {}).get("total_tokens") if isinstance(data.get("agent_result"), dict) else 0)
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
            data.get("verifier_summary") or data.get("final_error") or data.get("error") or data.get("run_dir") or "",
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
    trial_dir = trial_dir_for_result_path(path)
    if not trial_dir:
        return {"available": False}
    cost_path = trial_dir / "cost.json"
    if not cost_path.exists():
        result_path = trial_dir / "result.json"
        if result_path.exists():
            try:
                result = read_json(result_path)
                agent_result = result.get("agent_result") if isinstance(result.get("agent_result"), dict) else {}
                input_total = int(agent_result.get("n_input_tokens") or 0)
                cache_hit = int(agent_result.get("n_cache_tokens") or 0)
                output = int(agent_result.get("n_output_tokens") or 0)
                if input_total or cache_hit or output:
                    input_pure = max(0, input_total - cache_hit)
                    billable = input_pure * 6 / 1_000_000 + cache_hit * 1.2 / 1_000_000 + output * 24 / 1_000_000
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
                return {"available": False, "cost_path": str(cost_path), "error": compact(str(exc), 300)}
        trajectory_path = trial_dir / "agent" / "trajectory.json"
        if trajectory_path.exists():
            try:
                trajectory = read_json(trajectory_path)
                final = trajectory.get("final_metrics") if isinstance(trajectory.get("final_metrics"), dict) else {}
                input_total = int(final.get("total_prompt_tokens") or final.get("total_input_tokens") or 0)
                cache_hit = int(final.get("total_cached_tokens") or 0)
                output = int(final.get("total_completion_tokens") or final.get("total_output_tokens") or 0)
                if input_total or cache_hit or output:
                    input_pure = max(0, input_total - cache_hit)
                    billable = input_pure * 6 / 1_000_000 + cache_hit * 1.2 / 1_000_000 + output * 24 / 1_000_000
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
                return {"available": False, "cost_path": str(cost_path), "error": compact(str(exc), 300)}
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


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _pct_delta(base: float | None, new: float | None) -> float | None:
    if base in (None, 0) or new is None:
        return None
    return ((new - base) / base) * 100.0


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
    baseline_reward = _float_or_none(baseline.get("baseline_reward"))
    previous_reward = _float_or_none(previous.get("baseline_reward"))
    baseline_bill = _float_or_none(baseline_cost.get("billable_cost_cny"))
    previous_bill = _float_or_none(previous_cost.get("billable_cost_cny"))
    reward_delta = None if baseline_reward is None or previous_reward is None else previous_reward - baseline_reward
    cost_delta_pct = _pct_delta(baseline_bill, previous_bill)
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
    elif reward_delta is not None and abs(reward_delta) <= 1e-9 and cost_delta_pct is not None and cost_delta_pct > 1e-9:
        failure_type = "reward_same_cost_up"
        objective = "reduce_cost_after_no_reward_gain"
        guidance = [
            "The previous rewrite did not improve reward and increased billable cost. Make the next rewrite shorter and less route-expanding.",
            "Keep only public clarifications directly tied to repeated reads, command loops, output-format hesitation, or delayed stopping.",
            "Do not add extra validation, analysis standards, domain preferences, or verbose explanations.",
        ]
    elif reward_delta is not None and reward_delta > 1e-9 and cost_delta_pct is not None and cost_delta_pct > 10.0:
        failure_type = "reward_up_cost_up"
        objective = "compact_successful_rewrite"
        guidance = [
            "The previous rewrite improved reward but increased cost. Preserve the likely reward-critical public clarifications and compress everything else.",
            "Do not remove the output/interface clarifications that plausibly caused the reward gain.",
        ]
    elif reward_delta is not None and reward_delta > 1e-9:
        failure_type = "reward_up"
        objective = "keep_or_lightly_compact_success"
        guidance = ["The previous rewrite improved reward. Prefer keeping it or lightly compacting without changing semantics."]
    elif cost_delta_pct is not None and cost_delta_pct < -1e-9:
        failure_type = "reward_same_cost_down"
        objective = "stop_or_light_compact"
        guidance = ["The previous rewrite already reduced cost without reward loss. A further round should be minimal or no-op."]
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

    Iterative optimization round {round_feedback.get('round_index')}: {round_feedback.get('round_objective')}

    The previous accepted rewrite has already been rerun. Use the previous rerun result as feedback, not as a hidden answer source.
    Observed previous-round failure type: {round_feedback.get('failure_type')}.
    Baseline reward: {round_feedback.get('baseline_reward')}; previous rewrite reward: {round_feedback.get('previous_reward')}; reward delta: {round_feedback.get('reward_delta_vs_baseline')}.
    Baseline billable cost CNY: {round_feedback.get('baseline_billable_cost_cny')}; previous rewrite billable cost CNY: {round_feedback.get('previous_billable_cost_cny')}; cost delta pct: {round_feedback.get('cost_delta_pct_vs_baseline')}.

    Current round guidance:
    {guidance}

    Keep the output as a complete final instruction.md. Do not mention rounds, previous runs, costs, trajectories, model/CLI, hidden evaluators, tests, checker behavior, or gold answers in the rewritten instruction.
    """).strip()


def ensure_empty_dir(path: Path, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise SystemExit(f"refusing to overwrite non-empty output dir: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_agent_task(
    *,
    original_task_root: Path,
    task_id: str,
    rewritten_instruction: str,
    runner_config: Path,
    model: str,
    cli: str,
    eval_command: str,
    default_timeout_sec: int,
    attempt: int,
    run_root: Path,
) -> dict[str, Any]:
    variant_task_root = run_root / "variant_task_root"
    variant_task_dir = variant_task_root / task_id
    source_task_dir = original_task_root / task_id
    shutil.copytree(source_task_dir, variant_task_dir, dirs_exist_ok=True)
    write_text(variant_task_dir / "instruction.md", rewritten_instruction)

    task = load_task_spec(variant_task_root, task_id, eval_command, default_timeout_sec)
    exp = Experiment(
        name="agentmeter_opt_one_task",
        manifest="",
        models=(model,),
        clis=(cli,),
        runner="api",
        attempts=1,
        timeout_sec=task.timeout_sec or default_timeout_sec,
        record_trajectory=True,
        save_stdout=True,
        save_stderr=True,
        save_patch=True,
        resume=False,
    )
    api_configs = load_api_configs(runner_config)
    api_lookup(api_configs, model, cli)
    rerun_root = run_root / "rerun"
    summary = run_attempt(task, variant_task_root, rerun_root, model, cli, attempt, exp, api_configs)
    return {
        "summary": summary,
        "run_dir": summary.get("run_dir"),
        "variant_task_dir": str(variant_task_dir),
    }


def configure_gepa_call(oa_module: Any, args: argparse.Namespace, result_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    kwargs: dict[str, Any] = {}
    meta: dict[str, Any] = {"config_mode": "none"}
    optimize_sig = inspect.signature(oa_module.optimize_anything)
    if hasattr(oa_module, "GEPAConfig") and hasattr(oa_module, "EngineConfig"):
        engine_cls = oa_module.EngineConfig
        gepa_cls = oa_module.GEPAConfig
        try:
            engine_sig = inspect.signature(engine_cls)
            engine_kwargs = {}
            if "max_metric_calls" in engine_sig.parameters:
                engine_kwargs["max_metric_calls"] = args.max_metric_calls
            if "run_dir" in engine_sig.parameters:
                engine_kwargs["run_dir"] = str(result_dir / "gepa_engine")
            if "parallel" in engine_sig.parameters:
                engine_kwargs["parallel"] = False
            if "display_progress_bar" in engine_sig.parameters:
                engine_kwargs["display_progress_bar"] = False
            engine = engine_cls(**engine_kwargs)
            gepa_sig = inspect.signature(gepa_cls)
            gepa_kwargs = {}
            if "engine" in gepa_sig.parameters:
                gepa_kwargs["engine"] = engine
            if hasattr(oa_module, "ReflectionConfig") and "reflection" in gepa_sig.parameters:
                reflection_cls = oa_module.ReflectionConfig
                reflection_sig = inspect.signature(reflection_cls)
                reflection_kwargs = {}
                if "reflection_lm" in reflection_sig.parameters and args.reflection_model:
                    reflection_kwargs["reflection_lm"] = args.reflection_model
                gepa_kwargs["reflection"] = reflection_cls(**reflection_kwargs)
                meta["reflection_signature"] = str(reflection_sig)
            if args.candidate_only and args.offline_until_accepted and "stop_callbacks" in gepa_sig.parameters:
                try:
                    stop_module = importlib.import_module("gepa.utils.stop_condition")
                    gepa_kwargs["stop_callbacks"] = stop_module.ScoreThresholdStopper(1.0)
                    meta["stop_callback"] = "ScoreThresholdStopper(threshold=1.0)"
                except Exception as exc:
                    meta["stop_callback_error"] = str(exc)
            kwargs["config"] = gepa_cls(**gepa_kwargs)
            meta["config_mode"] = "GEPAConfig+EngineConfig"
            meta["engine_signature"] = str(engine_sig)
            meta["gepa_signature"] = str(gepa_sig)
        except Exception as exc:
            meta["config_error"] = str(exc)
    if "max_metric_calls" in optimize_sig.parameters and "config" not in kwargs:
        kwargs["max_metric_calls"] = args.max_metric_calls
        meta["config_mode"] = "direct_max_metric_calls"
    if args.reflection_model and "reflection_lm" in optimize_sig.parameters:
        kwargs["reflection_lm"] = args.reflection_model
        meta["reflection_lm"] = args.reflection_model
    return kwargs, meta


def extract_best_candidate(result: Any, seed_candidate: str) -> str:
    if hasattr(result, "best_candidate"):
        best = result.best_candidate
    elif isinstance(result, dict):
        best = result.get("best_candidate") or result.get("best")
    else:
        best = getattr(result, "best", None)
    if isinstance(best, str):
        return best
    if isinstance(best, dict):
        for key in ("candidate", "instruction", "text", "artifact", "value"):
            if isinstance(best.get(key), str):
                return best[key]
    return seed_candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="dm-csv-001")
    parser.add_argument("--task-root", type=Path, required=True)
    parser.add_argument("--seed-instruction", type=Path, help="Optional previous accepted rewritten instruction to use as GEPA seed. Safety is still checked against the original task instruction.")
    parser.add_argument("--baseline-result", type=Path)
    parser.add_argument("--previous-result", type=Path, help="Previous accepted rewrite rerun result/trajectory for iterative round feedback.")
    parser.add_argument("--round-index", type=int, default=1, help="1 for baseline adaptation; >=2 for iterative feedback repair/compaction rounds.")
    parser.add_argument("--combo", default="qwen36_kimi_cli")
    parser.add_argument("--model")
    parser.add_argument("--cli")
    parser.add_argument("--runner-config", type=Path)
    parser.add_argument("--eval-command", default="harbor run -p {task_dir} -a oracle")
    parser.add_argument("--max-metric-calls", type=int, default=5)
    parser.add_argument("--max-real-reruns", type=int, default=2)
    parser.add_argument("--candidate-only", action="store_true", help="Do not run the agent; select safe rewritten instruction candidates for later benchmark validation.")
    parser.add_argument("--offline-until-accepted", action="store_true", help="In candidate-only mode, continue offline GEPA proposals until an accepted candidate is found or max metric calls is reached.")
    parser.add_argument("--adaptation-mode", choices=["strict", "combo_adapted", "generic_no_trajectory"], default="strict")
    parser.add_argument("--default-timeout-sec", type=int, default=900)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--reflection-model")
    parser.add_argument("--max-trajectory-evidence-events", type=int, default=10)
    parser.add_argument("--allow-proxy", action="store_true", help="Keep HTTP(S)/ALL_PROXY environment variables for reflection LLM calls. By default they are cleared.")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "generated_reports" / "agentmeter_opt_min")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

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
    ensure_empty_dir(result_dir, args.overwrite)
    original_instruction = original_instruction_path.read_text(encoding="utf-8")
    seed_instruction_path = args.seed_instruction.resolve() if args.seed_instruction else original_instruction_path
    if not seed_instruction_path.exists():
        raise SystemExit(f"seed instruction not found: {seed_instruction_path}")
    seed_instruction = seed_instruction_path.read_text(encoding="utf-8")
    baseline = load_baseline_result(args.baseline_result, args.task_id, args.combo)
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
    objective = objective_for_mode(args.adaptation_mode, baseline_passed=bool(baseline["baseline_passed"]))
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
        "seed_differs_from_original": " ".join(seed_instruction.split()) != " ".join(original_instruction.split()),
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
        raise SystemExit("GEPA is not installed. Install official package first: `pip install gepa` or `pip install git+https://github.com/gepa-ai/gepa.git`.")
    if not args.candidate_only:
        if not runner_config:
            raise SystemExit("no runner config found; pass --runner-config or create configs/runners.local.yaml")
        if not runner_connected:
            raise SystemExit(f"runner config {runner_config} does not provide a route for model={model!r}, cli={cli!r}")

    oa_module = importlib.import_module("gepa.optimize_anything")
    optimize_anything = getattr(oa_module, "optimize_anything")
    optimize_kwargs, api_meta = configure_gepa_call(oa_module, args, result_dir)
    setup["gepa_info"]["resolved_api"] = api_meta
    write_json(result_dir / "gepa_setup.json", setup)

    state = {"metric_calls": 0, "real_reruns": 0}
    history: list[dict[str, Any]] = []
    candidate_cache: dict[str, dict[str, Any]] = {}
    rejection_feedback_memory: list[dict[str, Any]] = []

    def evaluator(candidate: str) -> float:
        state["metric_calls"] += 1
        candidate_key = " ".join(candidate.split())
        call_dir = result_dir / "metric_calls" / f"metric_call_{state['metric_calls']:03d}"
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
            "baseline_trajectory_evidence": baseline["trajectory_evidence"] if adaptation_policy.get("uses_trajectory_feedback", True) else {},
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
            "trajectory_summary": baseline["trajectory_summary"] if adaptation_policy.get("uses_trajectory_feedback", True) else "",
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
                    else "Use this trajectory/result as feedback for the current seed candidate. In multi-round refinement this should be the rerun result of the previous accepted instruction."
                ),
            },
        }
        if hasattr(oa_module, "log"):
            oa_module.log("safety_result=" + json.dumps(safety, ensure_ascii=False))
            oa_module.log("diff_summary=" + json.dumps(diff, ensure_ascii=False))
            if adaptation_policy.get("uses_trajectory_feedback", True):
                oa_module.log("trajectory_efficiency_feedback=" + json.dumps({
                    "route_profile": baseline["trajectory_evidence"].get("route_profile", {}),
                    "friction_signals": baseline["trajectory_evidence"].get("friction_signals", []),
                    "rewrite_guidance": baseline["trajectory_evidence"].get("rewrite_guidance", []),
                    "route_decision_points": baseline["trajectory_evidence"].get("route_decision_points", []),
                    "evidence_chains": baseline["trajectory_evidence"].get("evidence_chains", []),
                    "previous_rejection_feedback": rejection_feedback_memory[-3:],
                }, ensure_ascii=False))
            else:
                oa_module.log("public_only_rewrite_mode=" + json.dumps({
                    "uses_trajectory_feedback": False,
                    "previous_rejection_feedback": rejection_feedback_memory[-3:],
                }, ensure_ascii=False))
            oa_module.log("round_feedback=" + json.dumps(round_feedback, ensure_ascii=False))
            oa_module.log("baseline_summary=" + json.dumps({
                key: value for key, value in baseline.items() if key != "trajectory_evidence"
            }, ensure_ascii=False))

        rerun_info = None
        cached = candidate_cache.get(candidate_key)
        if cached:
            score = float(cached["score"])
            side_info.update(cached["side_info"])
            side_info["score_reason"] = "cached_" + str(side_info.get("score_reason") or "evaluation")
            rerun_info = cached.get("rerun_info")
        elif safety["status"] == "fail":
            score = 0.0
            side_info["score_reason"] = "safety_fail"
            side_info["rejection_feedback_for_next_candidate"] = rejection_feedback_from_safety(safety)
        elif safety["status"] == "needs_manual_review":
            score = 0.0
            side_info["score_reason"] = "needs_manual_review"
            side_info["rejection_feedback_for_next_candidate"] = rejection_feedback_from_safety(safety)
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
                score = 0.35 if should_explore_efficiency else (1.0 if baseline["baseline_passed"] else 0.0)
                score_reason = (
                    "baseline_passed_but_efficiency_friction_explore_rewrite"
                    if should_explore_efficiency
                    else "baseline_seed_candidate_no_rerun"
                )
            side_info.update(
                {
                    "passed": bool(baseline["baseline_passed"]),
                    "reward": float(baseline["baseline_reward"] or 0.0),
                    "tokens": int(baseline["baseline_tokens"] or 0),
                    "tool_calls": int(baseline["baseline_tool_calls"] or 0),
                    "token_efficiency_bonus": 0.0,
                    "score_reason": score_reason,
                    "rejection_feedback_for_next_candidate": {
                        "reason": "The candidate is identical to the current seed instruction. For this refinement round, propose a safe changed instruction that addresses the previous rerun regression or cost increase.",
                        "round_objective": round_feedback.get("round_objective"),
                        "failure_type": round_feedback.get("failure_type"),
                        "allowed_fix": "Keep the same task interface, but rewrite public-facing requirements, output/completion conditions, or organization to reduce the observed route friction.",
                    } if args.candidate_only else {},
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
        elif state["real_reruns"] >= args.max_real_reruns:
            score = 0.0
            side_info["score_reason"] = "rerun_budget_exhausted"
        else:
            state["real_reruns"] += 1
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
                reward = float(rerun_summary.get("reward") or (1.0 if rerun_summary.get("passed") else 0.0) or 0.0)
                passed = bool(rerun_summary.get("passed") or reward >= 1.0)
                rerun_tokens = int(rerun_summary.get("total_tokens") or 0)
                bonus = 0.0
                if reward > 0 and baseline["baseline_tokens"] and rerun_tokens and rerun_tokens < baseline["baseline_tokens"]:
                    bonus = min(0.2, 0.2 * ((baseline["baseline_tokens"] - rerun_tokens) / max(1, baseline["baseline_tokens"])))
                score = reward + bonus
                side_info.update(
                    {
                        "passed": passed,
                        "reward": reward,
                        "tokens": rerun_tokens,
                        "tool_calls": int(rerun_summary.get("tool_calls") or 0),
                        "trajectory_summary": compact(rerun_summary.get("error") or rerun_summary.get("run_dir") or "", 500),
                        "token_efficiency_bonus": round(bonus, 6),
                        "score_reason": "rerun_reward_token_score",
                    }
                )
                write_json(call_dir / "rerun_summary.json", rerun_summary)
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
        no_op_feedback = (side_info.get("rejection_feedback_for_next_candidate") or {}) if args.candidate_only and not diff.get("changed") else {}
        history_row = {
            "metric_call": state["metric_calls"],
            "real_reruns": state["real_reruns"],
            "score": score,
            "score_type": "acceptance_gate" if args.candidate_only else "performance_reward_token",
            "candidate_path": str(call_dir / "rewritten_instruction.md"),
            "safety_status": safety["status"],
            "violations": safety["violations"],
            "decision": safety["decision"],
            "semantic_preservation_status": safety.get("semantic_preservation_status"),
            "core_task_drift": safety.get("core_task_drift", []),
            "unsupported_added_preferences": safety.get("unsupported_added_preferences", []),
            "accepted_for_rerun": bool(args.candidate_only and safety["status"] == "pass" and diff.get("changed")),
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
            feedback = dict(no_op_feedback) if no_op_feedback else rejection_feedback_from_safety(safety)
            feedback.update({
                "metric_call": state["metric_calls"],
                "candidate_path": str(call_dir / "rewritten_instruction.md"),
                "score_reason": side_info.get("score_reason"),
            })
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

    best_summary = max(history, key=lambda row: row["score"], default=None)
    if best_summary and best_summary.get("candidate_path"):
        # Keep final text, score and side_info tied to the same metric call.
        # GEPA result.best_candidate may be absent or may not correspond to
        # the max(history) row in candidate-only/offline modes.
        best_instruction = Path(best_summary["candidate_path"]).read_text(encoding="utf-8")
    else:
        # If GEPA cannot expose a best candidate, fall back to the current
        # seed instruction, not the original instruction. This preserves
        # round-2/round-N refinement state.
        best_instruction = extract_best_candidate(result, seed_instruction)
    final_safety = safety_gate_for_mode(args.adaptation_mode, original_instruction, best_instruction)
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

    optimized_passed = bool(best_summary and best_summary["score"] >= 1.0) if not args.candidate_only else None
    optimized_tokens = 0
    optimized_reward = None if args.candidate_only else 0.0
    rewritten_instruction_path = result_dir / "best_rewritten_instruction.md"
    if best_summary:
        side_info = read_json(best_summary["side_info_path"])
        optimized_tokens = int(side_info.get("tokens") or 0)
        if not args.candidate_only:
            optimized_reward = float(side_info.get("reward") or 0.0)
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
        "baseline_passed": bool(baseline["baseline_passed"]),
        "baseline_reward": float(baseline["baseline_reward"] or 0.0),
        "optimized_passed": optimized_passed,
        "optimized_reward": optimized_reward,
        "candidate_only": bool(args.candidate_only),
        "accepted_candidate": bool(args.candidate_only and final_safety["status"] == "pass" and diff_summary(original_instruction, best_instruction).get("changed")),
        "accepted_candidate_meaning": "candidate-only safety/diff accepted for external rerun; not an optimization-success claim" if args.candidate_only else "not_applicable",
        "accepted_candidate_is_optimization_success": False if args.candidate_only else None,
        "optimization_success_requires_external_rerun": bool(args.candidate_only),
        "accepted_candidates_path": str(accepted_candidates_path) if accepted_candidates_path.exists() else "",
        "rejected_candidates_path": str(rejected_candidates_path) if rejected_candidates_path.exists() else "",
        "rejected_candidate_count": sum(1 for row in history if row.get("rejected_for_regeneration")),
        "best_score": best_summary["score"] if best_summary else None,
        "score_type": "acceptance_gate" if args.candidate_only else "performance_reward_token",
        "baseline_tokens": int(baseline["baseline_tokens"] or 0),
        "baseline_efficiency_friction": efficiency_friction,
        "optimized_tokens": optimized_tokens,
        "token_delta_pct": (
            ""
            if args.candidate_only
            else round(((optimized_tokens - baseline["baseline_tokens"]) / baseline["baseline_tokens"]) * 100, 4) if baseline["baseline_tokens"] else ""
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
        "metric_calls": state["metric_calls"],
        "real_reruns": state["real_reruns"],
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

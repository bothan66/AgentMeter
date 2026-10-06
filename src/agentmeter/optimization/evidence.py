"""Extract task-facing evidence and route friction from recorded trajectories."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agentmeter.harness import read_json

from .text import compact


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
        for tok in re.findall(
            r"[A-Za-z_][A-Za-z0-9_]{2,}|/[A-Za-z0-9_./+-]+|[A-Za-z0-9_.+-]+\.(?:csv|json|txt|md|py|tsv|xlsx|pdf)",
            text or "",
        )
        if len(tok) >= 3
    }


def extract_public_anchors(
    public_instruction: str, *, max_anchors: int = 12
) -> list[dict[str, Any]]:
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
        has_code_or_path = (
            "`" in line
            or "/" in line
            or re.search(r"\b\w+\.(?:csv|json|txt|md|py|tsv|xlsx|pdf)\b", line, flags=re.I)
        )
        has_interface = bool(
            re.search(
                r"\b(class|def|function|method|return|returns|write|save|output|input|format|schema|must|exactly|if|when|otherwise|edge|expired|priority|fifo|thread-safe|concurrent)\b",
                lowered,
            )
        )
        has_signature = bool(
            re.search(
                r"\b(?:class|def)\s+[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*\([^)]*\)\s*(?:->\s*[^`]+)?",
                line,
            )
        )
        if not (has_code_or_path or has_interface or has_signature):
            continue
        if line in seen:
            continue
        seen.add(line)
        if has_signature:
            kind = "public_interface_signature"
        elif has_code_or_path:
            kind = "public_file_or_output_contract"
        elif re.search(
            r"\b(if|when|otherwise|expired|priority|fifo|concurrent|thread-safe|must|exactly)\b",
            lowered,
        ):
            kind = "public_boundary_condition"
        else:
            kind = "public_requirement"
        anchors.append(
            {
                "anchor_id": f"anchor_{len(anchors) + 1:02d}",
                "line_no": idx + 1,
                "anchor_type": kind,
                "text": compact(line, 360),
                "tokens": sorted(_tokens_for_overlap(line))[:30],
            }
        )
        if len(anchors) >= max_anchors:
            break
    return anchors


def _route_decision_kind(text: str, tools: list[dict[str, Any]]) -> str:
    lowered = text.lower()
    if re.search(
        r"\b(schema|format|column|header|json|csv|output path|result file|sample)\b", lowered
    ):
        return "output_contract_choice"
    if re.search(
        r"\b(edge case|expired|ttl|lru|priority|fifo|concurrent|thread|return none|exception|boundary)\b",
        lowered,
    ):
        return "public_interface_boundary_choice"
    if re.search(
        r"\b(model|cluster|classifier|regression|feature|metric|parameter|threshold|validate)\b",
        lowered,
    ):
        return "modeling_or_metric_choice"
    if re.search(r"\b(try|instead|switch|alternative|fallback|retry|rerun|debug|fix)\b", lowered):
        return "repair_or_strategy_switch"
    if any(
        re.search(
            r"\b(pytest|test|python|bash|harbor)\b", str(item.get("target") or ""), flags=re.I
        )
        for item in tools
    ):
        return "validation_or_command_choice"
    if tools:
        return "tool_use_choice"
    return "interpretation_choice"


def _match_public_anchors(
    text: str, anchors: list[dict[str, Any]], *, limit: int = 3
) -> list[dict[str, Any]]:
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


def build_trajectory_evidence(
    path: Path | None, *, public_instruction: str = "", max_events: int = 8
) -> dict[str, Any]:
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
        token_total = (
            int(metrics.get("prompt_tokens") or 0)
            + int(metrics.get("completion_tokens") or 0)
            + int(metrics.get("cached_tokens") or 0)
        )
        obs = _obs_text(step)
        raw_text_blob = " ".join(
            [
                str(step.get("message") or ""),
                str(step.get("reasoning_content") or ""),
                obs,
            ]
        )
        text_blob = raw_text_blob.lower()
        tags = []
        if _contains_any(
            text_blob, ("error", "traceback", "permission denied", "failed", "exception")
        ):
            tags.append("error_or_feedback")
        matched_anchors = _match_public_anchors(raw_text_blob, public_anchors)
        obs_lower = obs.lower()
        if re.search(
            r"\b(assert|expected|actual|mismatch|not equal|wrong|test failed|failure|failed)\b",
            obs_lower,
        ) or re.search(r"\b(expected|actual|mismatch|not equal|wrong|test failed)\b", text_blob):
            tags.append("outcome_contradiction")
        if _contains_any(text_blob, ("saved", "output", "result", "csv", "json", "xlsx", "pdf")):
            tags.append("output_or_artifact")
        if _contains_any(
            text_blob,
            ("read", "understand", "structure", "format", "schema", "sample", "instruction"),
        ):
            tags.append("inspection_or_format_understanding")
        if any(
            anchor.get("anchor_type") in {"public_interface_signature", "public_boundary_condition"}
            for anchor in matched_anchors
        ) or re.search(
            r"\b(class|def|method|return|returns|exception|schema|column|header|field|format)\b",
            text_blob,
        ):
            tags.append("code_or_interface_boundary")
        if re.search(
            r"\b(i will|i need|we need|should|probably|maybe|assume|decide|try|instead|switch|fallback|looks like|seems)\b",
            text_blob,
        ):
            tags.append("route_decision")
        if tools:
            tags.append("tool_use")
        if any(
            _contains_any(
                str(item.get("target") or ""), ("pytest", "test", "python", "bash", "harbor")
            )
            for item in tools
        ):
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
        if (
            "route_decision" in tags
            or "code_or_interface_boundary" in tags
            or "output_or_artifact" in tags
        ):
            route_decision_points.append(
                {
                    "decision_id": f"decision_{len(route_decision_points) + 1:03d}",
                    "event_id": row["event_id"],
                    "decision_kind": _route_decision_kind(raw_text_blob, tools),
                    "summary": compact(
                        step.get("reasoning_content") or step.get("message") or obs, 360
                    ),
                    "public_basis": matched_anchors[:2],
                    "uncertainty_or_hesitation": bool(
                        re.search(
                            r"\b(probably|maybe|assume|seems|looks like|try|instead|fallback|not sure)\b",
                            text_blob,
                        )
                    ),
                    "downstream_signal": [
                        tag
                        for tag in tags
                        if tag
                        in {
                            "error_or_feedback",
                            "outcome_contradiction",
                            "high_token_step",
                            "output_or_artifact",
                        }
                    ],
                }
            )
        if tags:
            friction_signals.append(
                {
                    "event_id": f"step_{idx + 1:03d}",
                    "signals": tags,
                    "reason": compact(step.get("reasoning_content") or step.get("message"), 320),
                }
            )

    for target, count in sorted(read_targets.items()):
        if count >= 2:
            friction_signals.append(
                {
                    "event_id": "aggregate",
                    "signals": ["repeated_file_read"],
                    "target": target,
                    "count": count,
                }
            )
    for target, count in sorted(command_targets.items()):
        if count >= 2:
            friction_signals.append(
                {
                    "event_id": "aggregate",
                    "signals": ["repeated_command"],
                    "target": target,
                    "count": count,
                }
            )

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
    repeated_reads = [
        {"target": target, "count": count}
        for target, count in sorted(read_targets.items())
        if count >= 2
    ]
    repeated_commands = [
        {"target": target, "count": count}
        for target, count in sorted(command_targets.items())
        if count >= 2
    ]
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
            row
            for row in route_evidence
            if int(row["event_id"].split("_")[-1]) >= event_num
            and (
                {
                    "error_or_feedback",
                    "outcome_contradiction",
                    "output_or_artifact",
                    "high_token_step",
                }
                & set(row.get("route_tags") or [])
            )
        ][:2]
        if not outcomes and (decision.get("downstream_signal") or current.get("tool_calls")):
            outcomes = [current]
        if not decision.get("public_basis") and not outcomes:
            continue
        evidence_chains.append(
            {
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
            }
        )
        if len(evidence_chains) >= max(3, max_events // 2):
            break
    rewrite_guidance = []
    if repeated_reads:
        rewrite_guidance.append(
            "If public task text/artifacts allow it, consolidate input/output locations and file roles so the agent does not repeatedly inspect the same files."
        )
    if repeated_commands:
        rewrite_guidance.append(
            "If public requirements allow it, make completion/output conditions explicit so the agent can avoid repeated command/test loops."
        )
    if any("output_or_artifact" in row["route_tags"] for row in route_evidence):
        rewrite_guidance.append(
            "If public output contract is present, state the required output file, schema, ordering, and artifact role directly in final instruction text."
        )
    if any("code_or_interface_boundary" in row["route_tags"] for row in route_evidence):
        rewrite_guidance.append(
            "For code/API tasks, clarify public interface semantics, return values, boundary conditions, and completion behavior when the trajectory shows implementation or test-feedback confusion."
        )
    if any("outcome_contradiction" in row["route_tags"] for row in route_evidence):
        rewrite_guidance.append(
            "When public anchors and outcome contradictions align, prefer bounded clarifications of the public requirement instead of adding solver strategy or hidden test details."
        )
    if high_token_events:
        rewrite_guidance.append(
            "Prefer concise public clarifications that reduce long reasoning or route detours; do not add solver strategy."
        )
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

"""Audit rewritten instructions for public-interface and semantic preservation."""

from __future__ import annotations

import re
from typing import Any

PATH_RE = re.compile(
    r"`([^`\n]+)`|(/[\w./+-]+)|\b([\w./+-]+\.(?:csv|json|txt|md|py|sh|yaml|yml|toml|pdf|tsv))\b"
)
FILE_OR_PATH_RE = re.compile(r"/|[\w+-]+\.(?:csv|json|txt|md|py|sh|yaml|yml|toml|pdf|tsv)$", re.I)
LINE_KEYWORDS = (
    "must",
    "should",
    "write",
    "save",
    "output",
    "return",
    "create",
    "implement",
    "produce",
    "generate",
    "use",
    "file",
    "format",
    "input",
    "task",
)
FAIL_PATTERNS = {
    "hidden_evaluator": [
        r"\bhidden evaluator\b",
        r"\bhidden test",
        r"\bgold answer\b",
        r"\bgold output\b",
        r"\bground truth\b",
        r"\bchecker\.py\b",
        r"\bscor(?:e|ing) script\b",
        r"\breward\.txt\b",
        r"\bverifier\b",
        r"\btest_outputs\.py\b",
        r"\btests?/test",
        r"\bpeek\b.+\btests?\b",
    ],
    "solver_hint": [
        r"\buse (?:dynamic programming|dfs|bfs|dijkstra|a\*|astar|beam search|binary search|regex|pandas|numpy|scipy|cvxpy|gurobi|ortools)\b",
        r"\bsolve (?:this )?(?:using|with)\b",
        r"\bimplementation steps?\b",
        r"\balgorithm\b",
        r"\bsolver\b",
        r"\bdebug(?:ging)? advice\b",
    ],
    "implementation_route": [
        r"\basyncio\.PriorityQueue\b",
        r"\basyncio\.create_task\b",
        r"\bthreading\.Lock\b",
        r"\bcollections\.OrderedDict\b",
        r"\bOrderedDict\b",
        r"\bheapq\b",
        r"\bdeque\b",
        r"\binternal (?:queue|state|counter|data structure|storage)\b",
        r"\bbackground tasks?\b",
        r"\bspawn (?:the )?workers?\b",
        r"\bwrite, run, or debug\b",
        r"\bcustom test scripts?\b",
        r"\bindex\s*=\s*false\b",
        r"\bwithout the pandas dataframe index\b",
        r"\bwithout the dataframe index\b",
        r"\bpandas dataframe\b",
    ],
    "environment_fix": [
        r"\binstall package\b",
        r"\bpip install\b",
        r"\buv pip\b",
        r"\bchange dependency\b",
        r"\bpatch test\b",
        r"\bmodify tests?\b",
        r"\bchange runner\b",
        r"\bedit checker\b",
        r"\bfix the environment\b",
    ],
    "meta_instruction": [
        r"\bthink step by step\b",
        r"\bbe careful\b",
        r"\bverify thoroughly\b",
        r"\bdouble[- ]check\b",
        r"\bchain of thought\b",
        r"\breason carefully\b",
        r"\bdo not forget\b",
        r"\bmake sure to think\b",
    ],
    "difficulty_reduction": [
        r"\bonly need to\b",
        r"\bit is enough to\b",
        r"\byou can ignore\b",
        r"\bdo not need to\b",
        r"\bno need to\b",
        r"\bonly consider\b",
        r"\bat minimum\b",
        r"\bsmall subset\b",
    ],
}
REVIEW_PATTERNS = {
    "directional_guess": [
        r"\brather than\b",
        r"\binstead of\b",
        r"\bdefault to\b",
        r"\bassume\b",
        r"\bif not mentioned\b",
    ],
    "internal_info": [
        r"\binternal\b",
        r"\bprivate\b",
        r"\bhidden\b",
        r"\bunder the hood\b",
        r"\bimplementation detail\b",
    ],
}
SEMANTIC_PREFERENCE_PATTERNS = {
    "sorting_requirement": [
        r"\bsort(?:ed|ing)?\b",
        r"\balphabetical(?:ly)?\b",
        r"\bascending\b",
        r"\bdescending\b",
        r"\brow order\b",
    ],
    "rounding_requirement": [
        r"\bround(?:ed|ing)?\b",
        r"\b\d+\s*decimal places?\b",
        r"\b2 decimal places\b",
        r"\bprecision\b",
    ],
    "index_suppression": [
        r"\bindex\s*=\s*false\b",
        r"\bwithout the pandas dataframe index\b",
        r"\bwithout the dataframe index\b",
    ],
    "forced_full_enumeration": [
        r"\ball [a-z0-9 _-]+ must appear\b",
        r"\binclude all\b",
        r"\bno levels are skipped\b",
        r"\beven if the count is 0\b",
        r"\beven if .* is 0\b",
    ],
}
TASK_ACTION_PATTERNS = {
    "identify": [r"\bidentify\b", r"\bfind\b", r"\blocat(?:e|ing)\b"],
    "count": [r"\bcount\b", r"\bhow many\b", r"\bnumber of\b"],
    "calculate": [r"\bcalculate\b", r"\bcompute\b"],
    "classify": [r"\bclassify\b", r"\blabel\b", r"\bcategorize\b"],
    "extract": [r"\bextract\b"],
    "convert": [r"\bconvert\b", r"\btransform\b"],
    "generate": [r"\bgenerate\b", r"\bproduce\b", r"\bcreate\b"],
    "implement": [r"\bimplement\b", r"\bbuild\b"],
    "rank": [r"\brank\b", r"\bsort\b", r"\border\b"],
    "return": [r"\breturn\b", r"\bwrite\b", r"\bsave\b", r"\boutput\b"],
}


def _sentence_split(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [part.strip() for part in raw if part and part.strip()]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_paths(text: str) -> set[str]:
    found: set[str] = set()
    for match in PATH_RE.finditer(text):
        code_span, abs_path, file_name = match.groups()
        if code_span and FILE_OR_PATH_RE.search(code_span):
            found.add(code_span.strip("`"))
        if abs_path:
            found.add(abs_path.strip("`"))
        if file_name:
            found.add(file_name.strip("`"))
    return found


def _is_public_path_composition(path: str, original_paths: set[str]) -> bool:
    """Allow harmless compositions such as /app/output/ + result.csv."""
    normalized = path.strip("`")
    if "/" not in normalized:
        return False
    parts = normalized.rstrip("/").rsplit("/", 1)
    if len(parts) != 2:
        return False
    parent, name = parts
    parent_with_slash = parent + "/"
    return name in original_paths and (
        parent in original_paths or parent_with_slash in original_paths
    )


def _missing_paths_covered_by_composition(
    missing_paths: list[str], rewritten_paths: set[str], original_paths: set[str]
) -> bool:
    if not missing_paths:
        return True
    for path in missing_paths:
        covered = False
        for rewritten in rewritten_paths:
            if not _is_public_path_composition(rewritten, original_paths):
                continue
            parent, name = rewritten.rstrip("/").rsplit("/", 1)
            if path in {parent, parent + "/", name}:
                covered = True
                break
        if not covered:
            return False
    return True


def _salient_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"`{3,}\w*", line) or re.fullmatch(r"`{3,}", line):
            continue
        if re.fullmatch(r"#{1,6}\s+.+", line):
            continue
        if re.fullmatch(r"\*\*[^*]+:\*\*\s*.+", line):
            continue
        lowered = line.lower()
        if "`" in line or "/" in line or any(key in lowered for key in LINE_KEYWORDS):
            lines.append(line)
    return lines


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[A-Za-z0-9_.:/+-]+", text.lower()) if len(tok) >= 3}


def _line_covered(line: str, rewritten_lines: list[str]) -> bool:
    original_tokens = _tokenize(line)
    if not original_tokens:
        return True
    for candidate in rewritten_lines:
        overlap = original_tokens & _tokenize(candidate)
        if len(overlap) >= max(2, min(len(original_tokens), 4) // 2):
            return True
    return False


def _contains_pattern(text: str, patterns: list[str]) -> bool:
    normalized = _normalize(text)
    return any(re.search(pattern, normalized, flags=re.I) for pattern in patterns)


def _semantic_anchor_missing(original: str, rewritten: str) -> list[str]:
    missing: list[str] = []
    for label, patterns in SEMANTIC_PREFERENCE_PATTERNS.items():
        if _contains_pattern(rewritten, patterns) and not _contains_pattern(original, patterns):
            missing.append(label)
    return missing


def _core_task_sentences(text: str) -> list[str]:
    out: list[str] = []
    for sentence in _sentence_split(text):
        lowered = sentence.lower()
        if any(
            key in lowered
            for key in (
                "analyze",
                "identify",
                "count",
                "calculate",
                "classify",
                "extract",
                "convert",
                "generate",
                "write",
                "create",
                "implement",
                "build",
                "return",
            )
        ):
            out.append(sentence)
    return out


def _extract_task_actions(text: str) -> set[str]:
    normalized = _normalize(text)
    found: set[str] = set()
    for action, patterns in TASK_ACTION_PATTERNS.items():
        if any(re.search(pattern, normalized, flags=re.I) for pattern in patterns):
            found.add(action)
    return found


def _core_task_drift(original: str, rewritten: str) -> list[str]:
    rewritten_lines = _salient_lines(rewritten) + _sentence_split(rewritten)
    missing_core = [
        line for line in _core_task_sentences(original) if not _line_covered(line, rewritten_lines)
    ]
    original_actions = _extract_task_actions(" ".join(_core_task_sentences(original)))
    rewritten_actions = _extract_task_actions(" ".join(_core_task_sentences(rewritten)))
    removed_actions = sorted(
        action
        for action in original_actions
        if action not in rewritten_actions and action != "return"
    )
    if len(original_actions - {"return"}) >= 2 and removed_actions:
        missing_core.extend([f"missing_task_action:{action}" for action in removed_actions])
    return missing_core


def _semantic_preservation_audit(original: str, rewritten: str) -> dict[str, Any]:
    original_core_text = " ".join(_core_task_sentences(original))
    rewritten_core_text = " ".join(_core_task_sentences(rewritten))
    original_actions = sorted(_extract_task_actions(original_core_text))
    rewritten_actions = sorted(_extract_task_actions(rewritten_core_text))
    unsupported_preferences = _semantic_anchor_missing(original, rewritten)
    core_task_drift = _core_task_drift(original, rewritten)
    if core_task_drift:
        status = "fail"
    elif unsupported_preferences:
        status = "needs_manual_review"
    else:
        status = "pass"
    return {
        "semantic_preservation_status": status,
        "core_actions_original": original_actions,
        "core_actions_rewritten": rewritten_actions,
        "core_task_drift": core_task_drift,
        "unsupported_added_preferences": unsupported_preferences,
    }


def _find_added_pattern_violations(
    original: str, rewritten: str, groups: dict[str, list[str]]
) -> list[str]:
    original_norm = _normalize(original)
    rewritten_norm = _normalize(rewritten)
    violations: list[str] = []
    for label, patterns in groups.items():
        for pattern in patterns:
            if re.search(pattern, rewritten_norm, flags=re.I) and not re.search(
                pattern, original_norm, flags=re.I
            ):
                violations.append(label)
                break
    return violations


def _json_key_container_types(text: str) -> dict[str, str]:
    """Extract public JSON example key container shape: list vs scalar."""
    out: dict[str, str] = {}
    for match in re.finditer(r'"([^"\n]+)"\s*:\s*([\[\{"]|[-+]?\d|\.\.\.)', text or ""):
        key = match.group(1)
        marker = match.group(2)
        if marker == "[" or marker == "...":
            out[key] = "list"
        elif marker == "{":
            out[key] = "object"
        else:
            out[key] = "scalar"
    return out


def _csv_column_mentions(text: str) -> set[tuple[str, ...]]:
    columns: set[tuple[str, ...]] = set()
    for match in re.finditer(r"`([A-Za-z0-9_ -]+(?:\s*,\s*[A-Za-z0-9_ -]+)+)`", text or ""):
        cols = tuple(part.strip() for part in match.group(1).split(",") if part.strip())
        if len(cols) >= 2:
            columns.add(cols)
    return columns


def _public_interface_violations(original: str, rewritten: str) -> list[str]:
    violations: list[str] = []
    original_json = _json_key_container_types(original)
    rewritten_json = _json_key_container_types(rewritten)
    for key, shape in original_json.items():
        if key not in rewritten_json:
            violations.append(f"missing_json_key:{key}")
        elif rewritten_json[key] != shape:
            violations.append(f"changed_json_value_container:{key}:{shape}->{rewritten_json[key]}")

    original_csv = _csv_column_mentions(original)
    rewritten_csv = _csv_column_mentions(rewritten)
    for cols in original_csv:
        if cols not in rewritten_csv:
            violations.append("changed_or_removed_public_csv_columns:" + ",".join(cols))
    return violations


def _decision_for_status(status: str, changed: bool) -> str:
    if status == "fail":
        return "no_op"
    if status == "needs_manual_review":
        return "needs_manual_review"
    return "weak_edit" if changed else "no_op"


def instruction_safety_gate(
    original_instruction: str, rewritten_instruction: str
) -> dict[str, Any]:
    original = original_instruction or ""
    rewritten = rewritten_instruction or ""
    changed = _normalize(original) != _normalize(rewritten)
    if not rewritten.strip():
        return {
            "status": "fail",
            "violations": ["empty_rewrite"],
            "reason": "rewritten instruction is empty",
            "decision": "no_op",
        }
    if not changed:
        return {
            "status": "pass",
            "violations": [],
            "reason": "rewritten instruction is identical to the original after whitespace normalization",
            "decision": "no_op",
        }

    hard_violations = _find_added_pattern_violations(original, rewritten, FAIL_PATTERNS)
    review_violations = _find_added_pattern_violations(original, rewritten, REVIEW_PATTERNS)
    semantic_audit = _semantic_preservation_audit(original, rewritten)

    original_paths = _extract_paths(original)
    rewritten_paths = _extract_paths(rewritten)
    missing_paths = sorted(path for path in original_paths if path not in rewritten_paths)
    new_paths = sorted(
        path
        for path in rewritten_paths
        if path not in original_paths and not _is_public_path_composition(path, original_paths)
    )

    if missing_paths:
        hard_violations.append("missing_original_public_paths")
    suspicious_new_paths = [
        path
        for path in new_paths
        if re.search(
            r"(tests?/|checker|reward|solution|oracle|verifier|\.py$|\.sh$)", path, flags=re.I
        )
    ]
    if suspicious_new_paths:
        hard_violations.append("introduced_internal_or_new_file_paths")
    elif new_paths:
        review_violations.append("introduced_new_public_paths")

    original_lines = _salient_lines(original)
    rewritten_lines = _salient_lines(rewritten)
    missing_lines = [line for line in original_lines if not _line_covered(line, rewritten_lines)]
    if missing_lines:
        hard_violations.append("dropped_key_public_requirements")
    core_task_drift = list(semantic_audit["core_task_drift"])
    if core_task_drift:
        hard_violations.append("changed_core_task_objective")
    unsupported_semantic_preferences = list(semantic_audit["unsupported_added_preferences"])
    if unsupported_semantic_preferences:
        review_violations.append("unsupported_public_preference_addition")

    original_norm = _normalize(original)
    rewritten_norm = _normalize(rewritten)
    if len(rewritten_norm) < max(80, int(len(original_norm) * 0.55)):
        review_violations.append("rewrite_too_short")
    if len(rewritten_norm) > int(len(original_norm) * 2.5):
        review_violations.append("rewrite_too_long")

    overlap = _tokenize(original_norm) & _tokenize(rewritten_norm)
    base = max(1, len(_tokenize(original_norm)))
    overlap_ratio = len(overlap) / base
    if overlap_ratio < 0.25:
        review_violations.append("low_public_token_overlap")

    new_code_like_tokens = sorted(
        tok
        for tok in (_tokenize(rewritten) - _tokenize(original))
        if len(tok) >= 5
        and (
            "/" in tok
            or re.search(r"\.(csv|json|txt|md|py|sh|yaml|yml|toml|pdf|tsv)$", tok, flags=re.I)
        )
        and not _is_public_path_composition(tok, original_paths)
    )
    if new_code_like_tokens:
        review_violations.append("new_internal_like_tokens")

    hard_violations = sorted(set(hard_violations))
    review_violations = sorted(set(review_violations) - set(hard_violations))
    if hard_violations:
        details = []
        if missing_paths:
            details.append(f"missing_paths={missing_paths[:8]}")
        if suspicious_new_paths:
            details.append(f"new_internal_paths={suspicious_new_paths[:8]}")
        if missing_lines:
            details.append(f"dropped_lines={missing_lines[:4]}")
        if core_task_drift:
            details.append(f"core_task_drift={core_task_drift[:3]}")
        reason = (
            "; ".join(details)
            or "rewritten instruction crosses the allowed task-preservation boundary"
        )
        return {
            "status": "fail",
            "violations": hard_violations,
            "reason": reason,
            "decision": _decision_for_status("fail", changed),
            **semantic_audit,
        }
    if review_violations:
        details = []
        if new_paths:
            details.append(f"new_paths={new_paths[:8]}")
        if new_code_like_tokens:
            details.append(f"new_tokens={new_code_like_tokens[:8]}")
        if unsupported_semantic_preferences:
            details.append(f"unsupported_preferences={unsupported_semantic_preferences[:6]}")
        details.append(f"overlap_ratio={overlap_ratio:.2f}")
        return {
            "status": "needs_manual_review",
            "violations": review_violations,
            "reason": "; ".join(details),
            "decision": _decision_for_status("needs_manual_review", changed),
            **semantic_audit,
        }
    return {
        "status": "pass",
        "violations": [],
        "reason": "rewrite preserves public task interface and only clarifies existing public requirements",
        "decision": _decision_for_status("pass", changed),
        **semantic_audit,
    }


def combo_adapted_instruction_safety_gate(
    original_instruction: str, rewritten_instruction: str
) -> dict[str, Any]:
    """Looser gate for combo-specific task adaptation.

    This mode intentionally allows trajectory-informed public clarifications
    and public artifact references. It still blocks hidden evaluator leakage,
    environment changes, direct test/checker references, and explicit solver
    routes.
    """
    interface_violations = _public_interface_violations(
        original_instruction or "", rewritten_instruction or ""
    )
    if interface_violations:
        return {
            "status": "fail",
            "violations": ["changed_public_io_interface"],
            "reason": "; ".join(interface_violations[:8]),
            "decision": "no_op",
        }

    result = instruction_safety_gate(original_instruction, rewritten_instruction)
    original_paths = _extract_paths(original_instruction or "")
    rewritten_paths = _extract_paths(rewritten_instruction or "")
    missing_paths = sorted(path for path in original_paths if path not in rewritten_paths)
    if (
        result["status"] == "fail"
        and set(result.get("violations") or []) == {"missing_original_public_paths"}
        and _missing_paths_covered_by_composition(missing_paths, rewritten_paths, original_paths)
    ):
        return {
            "status": "pass",
            "violations": [],
            "reason": "combo-adapted rewrite combines original public output directory and filename into one equivalent path",
            "decision": "weak_edit",
        }
    if result["status"] != "needs_manual_review":
        if result["status"] == "pass" and result["decision"] == "weak_edit":
            result = dict(result)
            result["reason"] = "combo-adapted rewrite passes hard safety boundary"
        return result

    new_paths = sorted(
        path
        for path in rewritten_paths
        if path not in original_paths and not _is_public_path_composition(path, original_paths)
    )
    dangerous_new_paths = [
        path
        for path in new_paths
        if re.search(
            r"(tests?/|checker|reward|solution|oracle|verifier|test_outputs|\.py$|\.sh$)",
            path,
            flags=re.I,
        )
    ]
    if dangerous_new_paths:
        return {
            "status": "fail",
            "violations": ["introduced_internal_or_new_file_paths"],
            "reason": f"combo-adapted gate blocks internal paths={dangerous_new_paths[:8]}",
            "decision": "no_op",
            "semantic_preservation_status": result.get("semantic_preservation_status"),
            "core_actions_original": result.get("core_actions_original", []),
            "core_actions_rewritten": result.get("core_actions_rewritten", []),
            "core_task_drift": result.get("core_task_drift", []),
            "unsupported_added_preferences": result.get("unsupported_added_preferences", []),
        }

    hard_added = _find_added_pattern_violations(
        original_instruction or "",
        rewritten_instruction or "",
        {
            key: patterns
            for key, patterns in FAIL_PATTERNS.items()
            if key in {"hidden_evaluator", "environment_fix", "solver_hint", "implementation_route"}
        },
    )
    if hard_added:
        return {
            "status": "fail",
            "violations": sorted(set(hard_added)),
            "reason": "combo-adapted gate blocks hidden/checker/environment/solver leakage",
            "decision": "no_op",
            "semantic_preservation_status": result.get("semantic_preservation_status"),
            "core_actions_original": result.get("core_actions_original", []),
            "core_actions_rewritten": result.get("core_actions_rewritten", []),
            "core_task_drift": result.get("core_task_drift", []),
            "unsupported_added_preferences": result.get("unsupported_added_preferences", []),
        }

    review = set(result.get("violations") or [])
    allowed_review = {
        "introduced_new_public_paths",
        "new_internal_like_tokens",
        "directional_guess",
        "rewrite_too_long",
    }
    remaining = sorted(review - allowed_review)
    if remaining:
        return {
            "status": "needs_manual_review",
            "violations": remaining,
            "reason": "combo-adapted gate still needs review for non-public or semantic-preservation risk",
            "decision": "needs_manual_review",
            "semantic_preservation_status": result.get("semantic_preservation_status"),
            "core_actions_original": result.get("core_actions_original", []),
            "core_actions_rewritten": result.get("core_actions_rewritten", []),
            "core_task_drift": result.get("core_task_drift", []),
            "unsupported_added_preferences": result.get("unsupported_added_preferences", []),
        }
    return {
        "status": "pass",
        "violations": [],
        "reason": "combo-adapted rewrite only adds public/trajectory-informed clarifications and passes hard safety boundary",
        "decision": "weak_efficiency_edit" if "rewrite_too_long" not in review else "weak_edit",
    }

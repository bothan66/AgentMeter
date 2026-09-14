from __future__ import annotations

import csv
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_ts() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def read_yaml(path: str | Path) -> dict[str, Any]:
    lines: list[tuple[int, str]] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        lines.append((len(line) - len(line.lstrip(" ")), line.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines):
            return {}, index
        if lines[index][1].startswith("- "):
            items: list[Any] = []
            while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
                item = lines[index][1][2:].strip()
                items.append(parse_scalar(item))
                index += 1
            return items, index
        data: dict[str, Any] = {}
        while index < len(lines):
            line_indent, text = lines[index]
            if line_indent < indent:
                break
            if line_indent > indent:
                raise ValueError(f"unexpected indentation near {text}")
            key, raw_value = text.split(":", 1)
            raw_value = raw_value.strip()
            if raw_value:
                data[key.strip()] = parse_scalar(raw_value)
                index += 1
            else:
                if index + 1 >= len(lines) or lines[index + 1][0] <= indent:
                    data[key.strip()] = {}
                    index += 1
                else:
                    data[key.strip()], index = parse_block(index + 1, lines[index + 1][0])
        return data, index

    parsed, _ = parse_block(0, lines[0][0] if lines else 0)
    return parsed if isinstance(parsed, dict) else {}


def ensure_relative(path: str) -> str:
    p = Path(path)
    if p.is_absolute() or any(part == ".." for part in p.parts):
        raise ValueError(f"task path must be relative: {path}")
    return str(p)


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    suite: str
    relative_task_path: str
    difficulty: str
    domain: str
    tags: tuple[str, ...]
    eval_type: str
    eval_command: str
    timeout_sec: int | None

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "TaskSpec":
        return cls(
            task_id=row["task_id"].strip(),
            suite=row["suite"].strip(),
            relative_task_path=ensure_relative(row["relative_task_path"].strip()),
            difficulty=row["difficulty"].strip(),
            domain=row["domain"].strip(),
            tags=tuple(tag.strip() for tag in row.get("tags", "").replace("|", ";").split(";") if tag.strip()),
            eval_type=row["eval_type"].strip(),
            eval_command=row["eval_command"].strip(),
            timeout_sec=int(row["timeout_sec"]) if row.get("timeout_sec") else None,
        )


@dataclass(frozen=True)
class Experiment:
    name: str
    manifest: str
    models: tuple[str, ...]
    clis: tuple[str, ...]
    runner: str
    attempts: int
    timeout_sec: int
    record_trajectory: bool
    save_stdout: bool
    save_stderr: bool
    save_patch: bool
    resume: bool

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Experiment":
        data = read_yaml(path)
        return cls(
            name=str(data.get("name") or "experiment"),
            manifest=str(data["manifest"]),
            models=tuple(str(x) for x in data.get("models", [])),
            clis=tuple(str(x) for x in data.get("clis", [])),
            runner=str(data.get("runner") or "api"),
            attempts=int(data.get("attempts") or 1),
            timeout_sec=int(data.get("timeout_sec") or 600),
            record_trajectory=bool(data.get("record_trajectory", True)),
            save_stdout=bool(data.get("save_stdout", True)),
            save_stderr=bool(data.get("save_stderr", True)),
            save_patch=bool(data.get("save_patch", True)),
            resume=bool(data.get("resume", True)),
        )


@dataclass(frozen=True)
class ApiConfig:
    url: str
    method: str = "POST"
    api_key_env: str | None = None
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    payload: dict[str, Any] | None = None
    response_format: str = "agentmeter"
    poll_url: str | None = None
    poll_interval_sec: float = 2.0
    max_poll_sec: int | None = None


def load_manifest(path: str | Path) -> list[TaskSpec]:
    required = {"task_id", "suite", "relative_task_path", "difficulty", "domain", "tags", "eval_type", "eval_command", "timeout_sec"}
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"manifest missing columns: {sorted(missing)}")
        return [TaskSpec.from_row(row) for row in reader]


def load_api_configs(path: str | Path | None) -> dict[str, ApiConfig]:
    if path is None or not Path(path).exists():
        return load_api_configs(Path(__file__).resolve().parents[1] / "configs" / "runners.example.yaml")
    data = read_yaml(path)
    raw = data.get("api_runners") or {}
    out: dict[str, ApiConfig] = {}
    for name, cfg in raw.items():
        out[str(name)] = ApiConfig(
            url=str(cfg["url"]),
            method=str(cfg.get("method") or "POST").upper(),
            api_key_env=str(cfg["api_key_env"]) if cfg.get("api_key_env") else None,
            auth_header=str(cfg.get("auth_header") or "Authorization"),
            auth_scheme=str(cfg.get("auth_scheme") or "Bearer"),
            payload=dict(cfg.get("payload") or {}),
            response_format=str(cfg.get("response_format") or cfg.get("api_format") or "agentmeter"),
            poll_url=str(cfg["poll_url"]) if cfg.get("poll_url") else None,
            poll_interval_sec=float(cfg.get("poll_interval_sec") or 2),
            max_poll_sec=int(cfg["max_poll_sec"]) if cfg.get("max_poll_sec") else None,
        )
    return out


class Recorder:
    def __init__(self, path: Path, enabled: bool = True):
        self.path = path
        self.enabled = enabled
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def record(self, event_type: str, **payload: Any) -> None:
        if not self.enabled:
            return
        data = {"type": event_type, "timestamp": utc_ts(), **payload}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, sort_keys=True) + "\n")


def api_lookup(configs: dict[str, ApiConfig], model: str, cli: str) -> ApiConfig:
    for key in (f"{model}__{cli}", f"{model}.{cli}", cli, "default"):
        if key in configs:
            return configs[key]
    raise ValueError(f"no API config for {model}/{cli}")


def format_obj(value: Any, fields: dict[str, str]) -> Any:
    if isinstance(value, str):
        return value.format(**fields)
    if isinstance(value, dict):
        return {k: format_obj(v, fields) for k, v in value.items()}
    if isinstance(value, list):
        return [format_obj(v, fields) for v in value]
    return value


def stable_int(*parts: str, modulo: int = 10_000) -> int:
    return int(hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()[:12], 16) % modulo


def mock_api_response(payload: dict[str, Any], response_format: str = "agentmeter") -> dict[str, Any]:
    seed = stable_int(str(payload["task_id"]), str(payload["model"]), str(payload["cli"]), modulo=1_000_000)
    input_tokens = 800 + seed % 2200
    output_tokens = 200 + (seed // 7) % 900
    cache_read_tokens = (seed // 13) % 200
    cache_creation_tokens = 100 + (seed // 19) % 200
    cache_hit_tokens = cache_read_tokens
    marker_event = None
    if payload.get("mock_agent_write"):
        task_dir = Path(str(payload["task_dir"]))
        run_dir = Path(str(payload["run_dir"]))
        marker = {
            "task_id": payload["task_id"],
            "model": payload["model"],
            "cli": payload["cli"],
            "task_dir": str(task_dir),
            "run_dir": str(run_dir),
            "note": "mock agent wrote this marker in the copied task_dir/run_dir; oracle solution was not invoked",
        }
        write_json(task_dir / ".agentmeter_agent_marker.json", marker)
        write_json(run_dir / "agent_execution_marker.json", marker)
        marker_event = {"type": "agent_marker", "task_dir": str(task_dir), "run_dir": str(run_dir)}
    if response_format == "anthropic":
        events = [
            {
                "type": "usage",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cache_hit_tokens": cache_read_tokens,
            }
        ]
        if marker_event:
            events.append(marker_event)
        return {
            "id": f"msg_{seed}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": f"mock anthropic completed {payload['task_id']}\n"}],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": cache_creation_tokens,
                "cache_read_input_tokens": cache_read_tokens,
            },
            "trajectory_events": events,
        }
    if response_format == "responses":
        return {
            "id": f"resp_{seed}",
            "status": "completed",
            "output_text": f"mock responses completed {payload['task_id']}\n",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "input_token_details": {"cached_tokens": cache_hit_tokens},
            },
            "trajectory_events": [
                {
                    "type": "usage",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_tokens": 0,
                    "cache_hit_tokens": cache_hit_tokens,
                }
            ],
        }
    if response_format == "completions":
        return {
            "id": f"chatcmpl_{seed}",
            "choices": [{"message": {"role": "assistant", "content": f"mock completions completed {payload['task_id']}\n"}}],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "prompt_tokens_details": {"cached_tokens": cache_hit_tokens},
            },
            "trajectory_events": [
                {
                    "type": "usage",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_tokens": 0,
                    "cache_hit_tokens": cache_hit_tokens,
                }
            ],
        }
    return {
        "status": "completed",
        "stdout": f"mock API completed {payload['task_id']} for {payload['model']}/{payload['cli']}\n",
        "stderr": "",
        "summary": {
            "passed": True,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": 0,
            "cache_hit_tokens": cache_read_tokens,
            "total_tokens": input_tokens + output_tokens + cache_read_tokens,
            "total_cost_cny": round((input_tokens + output_tokens) / 1_000_000 * 0.8, 6),
            "turns": 2 + seed % 5,
            "tool_calls": 1 + seed % 7,
            "exit_code": 0,
            "error": None,
        },
        "trajectory_events": [
            {
                "type": "usage",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_creation_tokens": 0,
                "cache_hit_tokens": cache_read_tokens,
            }
        ],
    }


def api_headers(cfg: ApiConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if cfg.api_key_env:
        key = os.environ.get(cfg.api_key_env)
        if not key:
            raise ValueError(f"missing required environment variable: {cfg.api_key_env}")
        headers[cfg.auth_header] = f"{cfg.auth_scheme} {key}" if cfg.auth_scheme else key
    return headers


def http_request(cfg: ApiConfig, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    if url.startswith("mock://"):
        return mock_api_response(payload or {}, cfg.response_format.lower())
    data = json.dumps(payload or {}).encode("utf-8") if cfg.method != "GET" else None
    req = urllib.request.Request(url=url, data=data, headers=api_headers(cfg), method=cfg.method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"API HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    return json.loads(text) if text.strip() else {}


def extract_text_from_response(data: dict[str, Any], response_format: str) -> str:
    if data.get("stdout"):
        return str(data.get("stdout") or "")
    if response_format == "responses":
        if data.get("output_text"):
            return str(data["output_text"])
        chunks: list[str] = []
        for item in data.get("output") or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content") or []:
                if isinstance(content, dict) and content.get("text"):
                    chunks.append(str(content["text"]))
        return "\n".join(chunks)
    if response_format == "completions":
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            first = choices[0]
            message = first.get("message")
            if isinstance(message, dict) and message.get("content"):
                return str(message["content"])
            if first.get("text"):
                return str(first["text"])
    if response_format == "anthropic":
        chunks = []
        for item in data.get("content") or []:
            if isinstance(item, dict) and item.get("text"):
                chunks.append(str(item["text"]))
        return "\n".join(chunks)
    return ""


def normalize_api_response(data: dict[str, Any], cfg: ApiConfig) -> dict[str, Any]:
    """Normalize AgentMeter, Anthropic, Responses, and Completions responses."""

    if "summary" in data:
        return data

    response_format = cfg.response_format.lower()
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    input_tokens = 0
    output_tokens = 0
    cache_read_tokens = 0
    cache_creation_tokens = 0
    cache_hit_tokens = 0
    total_tokens = 0

    if response_format == "anthropic":
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        cache_read_tokens = int(usage.get("cache_read_input_tokens") or usage.get("cache_read_tokens") or 0)
        cache_creation_tokens = int(usage.get("cache_creation_input_tokens") or usage.get("cache_creation_tokens") or 0)
        cache_hit_tokens = cache_read_tokens
        total_tokens = input_tokens + output_tokens + cache_read_tokens + cache_creation_tokens
    elif response_format == "responses":
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        cache_read_tokens = int(usage.get("cache_read_tokens") or usage.get("input_token_details", {}).get("cached_tokens") or 0)
        cache_hit_tokens = cache_read_tokens
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    elif response_format == "completions":
        input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        cache_read_tokens = int(
            usage.get("cache_read_tokens")
            or usage.get("prompt_tokens_details", {}).get("cached_tokens")
            or usage.get("input_token_details", {}).get("cached_tokens")
            or 0
        )
        cache_hit_tokens = cache_read_tokens
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    else:
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        cache_read_tokens = int(usage.get("cache_read_tokens") or 0)
        cache_creation_tokens = int(usage.get("cache_creation_tokens") or 0)
        cache_hit_tokens = int(usage.get("cache_hit_tokens") or cache_read_tokens)
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens + cache_read_tokens)

    error = data.get("error")
    status = str(data.get("status") or "").lower()
    passed = not error and status not in {"failed", "error"}
    normalized = dict(data)
    normalized["stdout"] = extract_text_from_response(data, response_format)
    normalized.setdefault("stderr", str(error) if error else "")
    normalized["summary"] = {
        "passed": passed,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_creation_tokens": cache_creation_tokens,
        "cache_hit_tokens": cache_hit_tokens,
        "total_tokens": total_tokens,
        "total_cost_cny": float(usage.get("total_cost_cny") or usage.get("cost_cny") or 0.0),
        "turns": int(data.get("turns") or 0),
        "tool_calls": int(data.get("tool_calls") or 0),
        "exit_code": 0 if passed else 1,
        "error": str(error) if error else None,
    }
    return normalized


def run_api(cfg: ApiConfig, task: TaskSpec, model: str, cli: str, run_dir: Path, task_dir: Path, timeout_sec: int, recorder: Recorder) -> dict[str, Any]:
    fields = {
        "task_id": task.task_id,
        "model": model,
        "cli": cli,
        "task_dir": str(task_dir),
        "run_dir": str(run_dir),
        "timeout_sec": str(timeout_sec),
    }
    payload = {
        "task_id": task.task_id,
        "model": model,
        "cli": cli,
        "task_dir": str(task_dir),
        "run_dir": str(run_dir),
        "timeout_sec": timeout_sec,
        **format_obj(cfg.payload or {}, fields),
    }
    url = cfg.url.format(**fields)
    recorder.record("api_request", method=cfg.method, url=url, task_id=task.task_id, model=model, cli=cli)
    raw_response = http_request(cfg, url, payload)
    write_json(run_dir / "raw_response.json", raw_response)
    response = normalize_api_response(raw_response, cfg)
    write_json(run_dir / "normalized_response.json", response)
    started = time.monotonic()
    while str(response.get("status", "")).lower() in {"queued", "running", "pending"}:
        poll = str(response.get("poll_url") or cfg.poll_url or "").format(run_id=str(response.get("run_id") or response.get("id") or ""), **fields)
        if not poll:
            break
        if time.monotonic() - started > (cfg.max_poll_sec or timeout_sec):
            raise TimeoutError("API polling timed out")
        time.sleep(cfg.poll_interval_sec)
        raw_response = http_request(ApiConfig(url=poll, method="GET", response_format=cfg.response_format), poll, None)
        write_json(run_dir / "raw_response.json", raw_response)
        response = normalize_api_response(raw_response, cfg)
        write_json(run_dir / "normalized_response.json", response)
    return response


def copy_task(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))


def write_patch(original: Path, modified: Path, out: Path) -> None:
    lines: list[str] = []
    original_files = {p.relative_to(original) for p in original.rglob("*") if p.is_file()}
    modified_files = {p.relative_to(modified) for p in modified.rglob("*") if p.is_file()}
    for rel in sorted(original_files | modified_files):
        before_path = original / rel
        after_path = modified / rel
        try:
            before = before_path.read_text(encoding="utf-8").splitlines(keepends=True) if before_path.exists() else []
            after = after_path.read_text(encoding="utf-8").splitlines(keepends=True) if after_path.exists() else []
        except UnicodeDecodeError:
            continue
        if before != after:
            lines.extend(difflib.unified_diff(before, after, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
    out.write_text("".join(lines), encoding="utf-8")


def evaluate(task_dir: Path, command: str, timeout_sec: int, run_dir: Path, recorder: Recorder, task: TaskSpec, model: str, cli: str) -> dict[str, Any]:
    started = time.monotonic()
    task_dir_abs = task_dir.resolve()
    run_dir_abs = run_dir.resolve()
    command = command.format(
        task_dir=task_dir_abs,
        run_dir=run_dir_abs,
        task_id=task.task_id,
        model=model,
        cli=cli,
        timeout_sec=timeout_sec,
    )
    recorder.record("command", cmd=command)
    completed = subprocess.run(command, cwd=task_dir, shell=True, text=True, capture_output=True, timeout=timeout_sec, check=False)
    result = {
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "duration_sec": round(time.monotonic() - started, 3),
        "error": None if completed.returncode == 0 else "evaluation failed",
    }
    recorder.record("stdout", text=completed.stdout or "")
    recorder.record("stderr", text=completed.stderr or "")
    recorder.record("eval", passed=result["passed"])
    write_json(run_dir / "eval_result.json", result)
    return result


def attempt_dir(out: Path, task_id: str, model: str, cli: str, attempt: int) -> Path:
    return out / "tasks" / task_id / f"{model}__{cli}" / f"attempt_{attempt:03d}"


def complete_summary(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = read_json(path)
    except Exception:
        return False
    return bool(data.get("task_id") and data.get("model") and data.get("cli") and "passed" in data)


def run_attempt(task: TaskSpec, task_root: Path, out: Path, model: str, cli: str, attempt: int, exp: Experiment, api_configs: dict[str, ApiConfig]) -> dict[str, Any]:
    run_dir = attempt_dir(out, task.task_id, model, cli, attempt)
    run_dir.mkdir(parents=True, exist_ok=True)
    source_task = (task_root / task.relative_task_path).resolve()
    work_task = run_dir / "task"
    copy_task(source_task, work_task)
    recorder = Recorder(run_dir / "trajectory.jsonl", exp.record_trajectory)
    recorder.record("start", task_id=task.task_id, model=model, cli=cli)
    timeout_sec = task.timeout_sec or exp.timeout_sec
    write_json(run_dir / "run_meta.json", {"task_id": task.task_id, "suite": task.suite, "model": model, "cli": cli, "attempt": attempt, "timeout_sec": timeout_sec})
    started = time.monotonic()
    response = run_api(api_lookup(api_configs, model, cli), task, model, cli, run_dir, work_task, timeout_sec, recorder)
    stdout = str(response.get("stdout") or "")
    stderr = str(response.get("stderr") or "")
    (run_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    recorder.record("stdout", text=stdout)
    recorder.record("stderr", text=stderr)
    for ev in response.get("trajectory_events") or []:
        if isinstance(ev, dict):
            recorder.record(str(ev.get("type") or "event"), **{k: v for k, v in ev.items() if k != "type"})
    for line in str(response.get("trajectory_jsonl") or "").splitlines():
        if line.strip():
            try:
                ev = json.loads(line)
                recorder.record(str(ev.get("type") or "event"), **{k: v for k, v in ev.items() if k not in {"type", "timestamp"}})
            except json.JSONDecodeError:
                recorder.record("remote_trajectory", text=line)
    eval_result = evaluate(work_task, task.eval_command, timeout_sec, run_dir, recorder, task, model, cli)
    remote_summary = response.get("summary") if isinstance(response.get("summary"), dict) else {}
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    summary = {
        "task_id": task.task_id,
        "suite": task.suite,
        "difficulty": task.difficulty,
        "domain": task.domain,
        "tags": ";".join(task.tags),
        "model": model,
        "cli": cli,
        "attempt": attempt,
        "passed": bool(eval_result["passed"]),
        "total_tokens": int(remote_summary.get("total_tokens") or usage.get("total_tokens") or 0),
        "input_tokens": int(remote_summary.get("input_tokens") or usage.get("input_tokens") or 0),
        "output_tokens": int(remote_summary.get("output_tokens") or usage.get("output_tokens") or 0),
        "cache_read_tokens": int(remote_summary.get("cache_read_tokens") or usage.get("cache_read_tokens") or 0),
        "cache_creation_tokens": int(remote_summary.get("cache_creation_tokens") or usage.get("cache_creation_tokens") or 0),
        "cache_hit_tokens": int(remote_summary.get("cache_hit_tokens") or usage.get("cache_hit_tokens") or remote_summary.get("cache_read_tokens") or usage.get("cache_read_tokens") or 0),
        "total_cost_cny": float(remote_summary.get("total_cost_cny") or usage.get("total_cost_cny") or 0.0),
        "turns": int(remote_summary.get("turns") or 0),
        "tool_calls": int(remote_summary.get("tool_calls") or 0),
        "duration_sec": round(time.monotonic() - started, 3),
        "exit_code": int(remote_summary.get("exit_code") if remote_summary.get("exit_code") is not None else eval_result["exit_code"]),
        "error": None if eval_result["passed"] else eval_result["error"],
        "run_dir": str(run_dir),
    }
    if summary["total_tokens"] == 0:
        summary["total_tokens"] = summary["input_tokens"] + summary["output_tokens"] + summary["cache_read_tokens"]
    normalized_usage = {k: summary[k] for k in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "cache_hit_tokens", "total_tokens", "total_cost_cny")}
    write_json(run_dir / "usage.json", normalized_usage)
    write_json(run_dir / "normalized_usage.json", normalized_usage)
    write_patch(source_task, work_task, run_dir / "patch.diff")
    write_json(run_dir / "summary.json", summary)
    recorder.record("end", status="passed" if summary["passed"] else "failed")
    return summary


def run_experiment(exp: Experiment, task_root: Path, out: Path, runner_config: str | Path | None, resume: bool, force: bool, task_ids: set[str] | None = None) -> list[dict[str, Any]]:
    tasks = load_manifest(exp.manifest)
    api_configs = load_api_configs(runner_config)
    summaries = []
    for task in tasks:
        if task_ids and task.task_id not in task_ids:
            continue
        for model in exp.models:
            for cli in exp.clis:
                for attempt in range(1, exp.attempts + 1):
                    run_dir = attempt_dir(out, task.task_id, model, cli, attempt)
                    if not force and resume and complete_summary(run_dir / "summary.json"):
                        continue
                    summaries.append(run_attempt(task, task_root, out, model, cli, attempt, exp, api_configs))
    return summaries


def summarize_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((str(row.get("model", "")), str(row.get("cli", ""))), []).append(row)
    out = []
    for (model, cli), subset in sorted(groups.items()):
        passed = sum(1 for row in subset if str(row.get("passed")).lower() in {"true", "1", "yes", "passed"})
        tokens = sum(float(row.get("total_tokens") or 0) for row in subset)
        out.append(
            {
                "model": model,
                "cli": cli,
                "tasks": len(subset),
                "pass_count": passed,
                "pass_rate": passed / len(subset) if subset else 0.0,
                "total_tokens": tokens,
                "tokens_per_pass": tokens / passed if passed else "",
            }
        )
    return out

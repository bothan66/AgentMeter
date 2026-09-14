"""Sanitize public result and trajectory artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SENSITIVE_FIELD_FRAGMENTS = (
    ("author", "ization"),
    ("api", "_key"),
    ("api", "-key"),
    ("tok", "en"),
    ("sec", "ret"),
    ("pass", "word"),
    ("coo", "kie"),
    ("credential", ""),
)
RAW_TEXT_KEYS = {
    "prompt",
    "raw_prompt",
    "response",
    "raw_response",
    "messages",
    "request",
    "headers",
    "body",
    "content",
}


def _sensitive_names() -> set[str]:
    return {"".join(parts).lower() for parts in SENSITIVE_FIELD_FRAGMENTS}


SENSITIVE_NAMES = _sensitive_names()
HOME_RE = re.compile(r"/(?:Users|home)/[^\\s\"']+")
DRIVE_RE = re.compile(r"[A-Za-z]:\\\\[^\\s\"']+")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL_RE = re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s\"']+", re.I)


def sanitize_text(text: str) -> str:
    text = HOME_RE.sub("<LOCAL_PATH>", text)
    text = DRIVE_RE.sub("<LOCAL_PATH>", text)
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = IP_RE.sub("<IP>", text)
    text = URL_RE.sub("<URL>", text)
    return text


def _safe_key(key: str) -> str:
    lowered = key.lower()
    lowered = lowered.replace("-", "_")
    return lowered


def sanitize_object(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            safe = _safe_key(str(key))
            if safe in SENSITIVE_NAMES or safe in RAW_TEXT_KEYS:
                continue
            out[str(key)] = sanitize_object(item)
        return out
    if isinstance(value, list):
        return [sanitize_object(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_file(in_path: str | Path, out_path: str | Path) -> None:
    src = Path(in_path)
    dst = Path(out_path)
    data = json.loads(src.read_text(encoding="utf-8"))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(sanitize_object(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")


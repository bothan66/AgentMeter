from __future__ import annotations


def route_to_format(path: str) -> str:
    if path.endswith("/v1/messages"):
        return "anthropic"
    if path.endswith("/v1/responses"):
        return "responses"
    if path.endswith("/v1/chat/completions") or path.endswith("/v1/completions"):
        return "completions"
    return "agentmeter"

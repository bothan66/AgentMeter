from __future__ import annotations

from typing import Any

from scripts.harness_lib import mock_api_response


def make_response(payload: dict[str, Any], response_format: str) -> dict[str, Any]:
    return mock_api_response(payload, response_format=response_format)

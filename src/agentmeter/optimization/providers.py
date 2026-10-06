"""Resolve model routes and configure the optional GEPA reflection provider."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import inspect
import os
from pathlib import Path
from typing import Any

from agentmeter.harness import api_lookup, load_api_configs
from agentmeter.paths import find_repository

COMBO_ALIASES = {
    "qwen36_kimi_cli": ("Qwen3.6+", "kimi-cli"),
    "qwen36_qwen_coder": ("Qwen3.6+", "qwen-coder"),
    "qwen36_codex": ("Qwen3.6+", "codex"),
    "glm51_qwen_coder": ("GLM-5.1", "qwen-coder"),
    "glm51_qwencoder": ("GLM-5.1", "qwen-coder"),
}

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


def discover_runner_config(explicit: Path | None) -> Path | None:
    """Resolve an explicit runner file or discover the repository's local configuration."""
    if explicit:
        return explicit if explicit.exists() else None
    try:
        root = find_repository()
    except FileNotFoundError:
        root = Path.cwd()
    for path in (root / "configs/runners.local.yaml", root / "configs/runners/runners.local.yaml"):
        if path.exists():
            return path
    return None


def parse_combo(combo: str, model: str | None, cli: str | None) -> tuple[str, str]:
    """Resolve a saved combo name into the model and harness used by its API route."""
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
    raise SystemExit(
        f"cannot infer model/cli from combo={combo!r}; pass --model and --cli explicitly"
    )


def detect_gepa() -> dict[str, Any]:
    """Report installed GEPA capabilities without requiring the optional dependency."""
    info: dict[str, Any] = {
        "installed": False,
        "module_path": "",
        "version": "",
        "api": {},
        "error": "",
    }
    try:
        gepa = importlib.import_module("gepa")
        gepa_optimizer = importlib.import_module("gepa.optimize_anything")
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
        "optimize_anything_module": str(getattr(gepa_optimizer, "__file__", "")),
        "optimize_anything_signature": str(
            inspect.signature(getattr(gepa_optimizer, "optimize_anything"))
        ),
        "has_GEPAConfig": hasattr(gepa_optimizer, "GEPAConfig"),
        "has_EngineConfig": hasattr(gepa_optimizer, "EngineConfig"),
        "has_log": hasattr(gepa_optimizer, "log"),
    }
    return info


def runner_has_route(runner_config: Path | None, model: str, cli: str) -> bool:
    """Check local model-harness routing without contacting the runner service."""
    if not runner_config:
        return False
    try:
        api_lookup(load_api_configs(runner_config), model, cli)
        return True
    except Exception:
        return False


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
    if not os.environ.get("OPENAI_BASE_URL") and info["mapped_api_key_env"] in {
        "DASHSCOPE_API_KEY",
        "ALIBABA_CLOUD_API_KEY",
        "BAILIAN_API_KEY",
        "AGENTMETER_API_KEY",
    }:
        os.environ["OPENAI_BASE_URL"] = DEFAULT_REFLECTION_OPENAI_BASE_URL
        info["base_url"] = DEFAULT_REFLECTION_OPENAI_BASE_URL
    elif os.environ.get("OPENAI_BASE_URL"):
        info["base_url"] = str(os.environ.get("OPENAI_BASE_URL") or "")
    return info


def configure_gepa_call(
    gepa_optimizer: Any, args: argparse.Namespace, result_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build optimizer call options and record the detected GEPA API signatures."""
    kwargs: dict[str, Any] = {}
    meta: dict[str, Any] = {"config_mode": "none"}
    optimize_sig = inspect.signature(gepa_optimizer.optimize_anything)
    if hasattr(gepa_optimizer, "GEPAConfig") and hasattr(gepa_optimizer, "EngineConfig"):
        engine_cls = gepa_optimizer.EngineConfig
        gepa_cls = gepa_optimizer.GEPAConfig
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
            if hasattr(gepa_optimizer, "ReflectionConfig") and "reflection" in gepa_sig.parameters:
                reflection_cls = gepa_optimizer.ReflectionConfig
                reflection_sig = inspect.signature(reflection_cls)
                reflection_kwargs = {}
                if "reflection_lm" in reflection_sig.parameters and args.reflection_model:
                    reflection_kwargs["reflection_lm"] = args.reflection_model
                gepa_kwargs["reflection"] = reflection_cls(**reflection_kwargs)
                meta["reflection_signature"] = str(reflection_sig)
            if (
                args.candidate_only
                and args.offline_until_accepted
                and "stop_callbacks" in gepa_sig.parameters
            ):
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
    """Read candidate text from supported GEPA result shapes, falling back to the seed."""
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

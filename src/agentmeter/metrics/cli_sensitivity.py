"""Same-model cross-CLI sensitivity metrics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .agentmeter import as_records, population_std, summarize_agentmeter


def _range(values: list[float]) -> float:
    return max(values) - min(values) if values else 0.0


def compute_cli_sensitivity(rows: Any, score_field: str = "score") -> list[dict[str, Any]]:
    records = as_records(rows)
    by_model_cli: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_model_cli[(str(row.get("model", "")), str(row.get("cli", "")))].append(row)

    cells: list[dict[str, Any]] = []
    for (model, cli), subset in by_model_cli.items():
        summary = summarize_agentmeter(subset, group_by=())[0]
        if any(score_field in row and row.get(score_field) not in ("", None) for row in subset):
            score_values = [float(row[score_field]) for row in subset if row.get(score_field) not in ("", None)]
            summary["agentmeter_score"] = sum(score_values) / len(score_values)
        summary.update({"model": model, "cli": cli})
        cells.append(summary)

    out: list[dict[str, Any]] = []
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        by_model[cell["model"]].append(cell)
    for model, model_cells in sorted(by_model.items()):
        pass_rates = [float(c["pass_rate"]) for c in model_cells]
        token_rates = [float(c["tokens_per_pass"]) for c in model_cells if c["tokens_per_pass"] is not None]
        scores = [float(c["agentmeter_score"]) for c in model_cells]
        best = max(model_cells, key=lambda c: float(c["agentmeter_score"])) if model_cells else {}
        worst = min(model_cells, key=lambda c: float(c["agentmeter_score"])) if model_cells else {}
        out.append(
            {
                "model": model,
                "cli_count": len(model_cells),
                "best_cli": best.get("cli", ""),
                "worst_cli": worst.get("cli", ""),
                "pass_gap": _range(pass_rates),
                "token_gap": _range(token_rates),
                "score_gap": _range(scores),
                "cli_sensitivity": population_std(scores),
            }
        )
    return out


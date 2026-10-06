"""Retain descriptions using measured outcomes, independently of GEPA scores.

Reward is primary. Equal rewards are compared using recorded cost in a common
currency, then the size of the edit to Original. Missing cost is not zero and
cannot establish an efficiency improvement or a cost tie.
"""

from __future__ import annotations

import difflib
import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CandidateOutcome:
    candidate_id: str
    instruction: str
    reward: float | None
    passed: bool | None
    cost_usd: float | None = None
    cost_cny: float | None = None

    def __post_init__(self) -> None:
        if self.reward is not None and (
            not math.isfinite(self.reward) or not 0 <= self.reward <= 1
        ):
            raise ValueError("Observed reward must be finite and between zero and one")
        for cost in (self.cost_usd, self.cost_cny):
            if cost is not None and (not math.isfinite(cost) or cost < 0):
                raise ValueError("Recorded cost must be finite and nonnegative")


@dataclass(frozen=True)
class RetentionDecision:
    winner: CandidateOutcome
    reason: str
    unresolved_cost_ties: tuple[str, ...] = ()


def _common_costs(first: CandidateOutcome, second: CandidateOutcome) -> tuple[float, float] | None:
    for field in ("cost_usd", "cost_cny"):
        left, right = getattr(first, field), getattr(second, field)
        if left is not None and right is not None:
            return left, right
    return None


def _edit_size(original: str, rewritten: str) -> int:
    """Count changed characters, ignoring differences in whitespace only."""
    original, rewritten = " ".join(original.split()), " ".join(rewritten.split())
    return sum(
        end_a - start_a + end_b - start_b
        for operation, start_a, end_a, start_b, end_b in difflib.SequenceMatcher(
            None, original, rewritten, autojunk=False
        ).get_opcodes()
        if operation != "equal"
    )


def retain_candidate(
    original: CandidateOutcome, candidates: Sequence[CandidateOutcome]
) -> RetentionDecision:
    """Retain only a measured improvement over Original.

    If a same-reward cost comparison is unavailable, keep the incumbent and
    record the unresolved comparison. A higher reward can still win without
    known cost. Equal reward and equal known cost prefer the smaller edit;
    Original has edit size zero, so a neutral rewrite never replaces it.
    """
    if original.reward is None:
        return RetentionDecision(original, "original_reward_unavailable")
    winner = original
    reason = "no_measured_improvement"
    unresolved: list[str] = []
    for candidate in candidates:
        if candidate.reward is None:
            continue
        # Every retained rewrite must independently improve Original. Pairwise
        # comparison alone can switch currencies along a chain and accidentally
        # retain a candidate that is more expensive than Original.
        if candidate.reward < original.reward:
            continue
        if candidate.reward == original.reward:
            original_costs = _common_costs(candidate, original)
            if original_costs is None:
                unresolved.append(candidate.candidate_id)
                continue
            if original_costs[0] >= original_costs[1]:
                continue
        if candidate.reward > winner.reward:
            winner, reason = candidate, "higher_reward"
            unresolved.clear()
            continue
        if candidate.reward < winner.reward:
            continue
        costs = _common_costs(candidate, winner)
        if costs is None:
            unresolved.append(candidate.candidate_id)
            continue
        candidate_cost, winner_cost = costs
        if candidate_cost < winner_cost:
            winner, reason = candidate, "equal_reward_lower_recorded_cost"
        elif candidate_cost == winner_cost and _edit_size(
            original.instruction, candidate.instruction
        ) < _edit_size(original.instruction, winner.instruction):
            winner, reason = candidate, "equal_reward_and_cost_smaller_edit"
    return RetentionDecision(winner, reason, tuple(unresolved))

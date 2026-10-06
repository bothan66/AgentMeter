# AgentMeter-Opt: trajectory-guided descriptions

This module treats a SkillsBench `instruction.md` as the only optimizable task
artifact. The source pair's trajectory provides feedback for candidate
construction; the task environment and verifier stay fixed. The paper uses
Qwen3.7-Max as the construction model.

Install the pinned construction dependencies and generate candidates from a
saved Original trajectory:

```bash
python -m pip install -e '.[opt]'
agentmeter optimize \
  --task-id regex-log \
  --task-root benchmark_tasks/terminal_bench \
  --baseline-result /path/to/original/agent/trajectory.json \
  --combo qwen36_codex \
  --model 'Qwen3.6+' \
  --cli codex \
  --adaptation-mode combo_adapted \
  --candidate-only \
  --offline-until-accepted \
  --max-metric-calls 5 \
  --reflection-model openai/qwen3.7-max \
  --out-dir generated_reports/example
```

Export the reflection provider's credentials and base URL before this command.
The construction provider may differ from the evaluation provider; see
[provider setup](external_dependencies.md#provider-routing). `--candidate-only`
generates and screens descriptions without running the target agent.

Output artifacts:

- `original_instruction.md`: immutable semantic and safety anchor.
- `seed_instruction.md`: current optimization seed.
- `baseline_trajectory_evidence.json`: normalized trajectory feedback.
- `accepted_candidates.jsonl`: candidates passing the automatic safety gate.
- `rejected_candidates.jsonl`: rejected candidates and violation reasons.
- `gepa_task_result.json`: provenance and optimization summary.

Evaluate candidates on the source model–harness pair with the unchanged task
environment and verifier. Select by reward first and billable cost second,
then freeze the selected description for Self/Cross evaluation.

## Selection and recorded costs

The live branch separates **search feedback** from **final retention**.
GEPA's `reward + token-efficiency bonus` guides candidate exploration; it is
not the billable-cost metric and does not determine the retained description.
Final retention uses measured reward first, then recorded cost in a common
currency, with a smaller edit to Original breaking equal-reward/equal-cost
ties. A candidate must improve reward or keep reward at lower cost; otherwise
the output remains Original. `retention.json` records this decision separately
from the exploration scores. Partial rewards are preserved, and a search
score above one does not imply that the verifier passed.

For live reruns, configure `--runner-config` and an explicit `--eval-command`.
`--baseline-result` always refers to the Original outcome; use
`--previous-result` and `--seed-instruction` for multi-round refinement.
Recorded costs come from the trial's `cost.json` when present, or explicit
USD/CNY totals in the result or runner summary. Unknown cost is not zero;
equal-reward candidates without comparable costs cannot establish savings.
The optimizer does not substitute a model-independent token-price estimate.

The study's unchanged [price snapshot](../configs/paper_model_pricing.json)
is included for accounting provenance. Archived paper tables still use
recorded `cost_usd`, without repricing. Candidate-only generation produces
proposals for later evaluation, not measured reward or cost improvements.

Review automatic preservation decisions against the original public
requirements. The [example notes](description_notes.md) explain representative
historical changes and their interpretation.

Implementation is split by responsibility under
[`src/agentmeter/optimization/`](../src/agentmeter/optimization/):
`evidence.py` extracts source-trajectory observations, `feedback.py` builds
round feedback, `costs.py` reads recorded charges, and `selection.py` applies
reward-first retention. `policy.py` chooses the optimization objective,
`safety.py` screens task preservation, and `optimize.py` coordinates construction.
Use `agentmeter optimize --help` for refinement and execution options, or
`agentmeter summarize --help` to collect generated optimization results.

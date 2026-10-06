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

Review automatic preservation decisions against the original public
requirements. The [example notes](description_notes.md) explain representative
historical changes and their interpretation.

Implementation is split by responsibility under
[`src/agentmeter/optimization/`](../src/agentmeter/optimization/):
`evidence.py` extracts source-trajectory observations, `feedback.py` builds
round feedback, `policy.py` chooses the optimization objective, `safety.py`
checks task preservation, and `optimize.py` coordinates candidate construction.
Use `agentmeter optimize --help` for refinement and execution options, or
`agentmeter summarize --help` to collect generated optimization results.

# AgentMeter-Opt instruction refinement

This module treats a SkillsBench `instruction.md` as the only optimizable task
artifact. It supports an initial candidate generated from an original Harbor
trajectory and later refinement from a previously accepted instruction.

```bash
python agentmeter_opt/optimize_instruction.py \
  --task-id TASK_ID \
  --task-root /path/to/tasks \
  --baseline-result /path/to/trajectory.json \
  --combo MODEL__HARNESS \
  --model MODEL \
  --cli HARNESS \
  --adaptation-mode combo_adapted \
  --candidate-only \
  --offline-until-accepted \
  --max-metric-calls 5 \
  --reflection-model openai/REFLECTION_MODEL \
  --out-dir generated_reports/example
```

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

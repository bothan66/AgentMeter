# Benchmark sources and adaptations

AgentMeter evaluates and adapts task instructions; it does not claim authorship
of the upstream benchmark content. Task files retain the licenses below rather
than being relicensed by AgentMeter's root MIT license.

| Local directory | Source | License retained here | Source revision |
|:--|:--|:--|:--|
| `skillsbench/` | [SkillsBench](https://github.com/benchflow-ai/skillsbench) | [Apache-2.0](skillsbench/LICENSE) | `be06b4995c75b384b9295b94d18a4531400bb821` |
| `da_code/` | [DA-Code](https://github.com/yiyihum/da-code) | [MIT, Jianwen Luo](da_code/LICENSE) | `b211daf51fdc9b52d5087c9df28ac50191bcabed` |
| `terminal_bench/` | [Terminal-Bench](https://github.com/laude-institute/terminal-bench), project-author-attributed local adaptations | [Apache-2.0](terminal_bench/LICENSE) | Original upstream revision not retained; the local task snapshot is included |

## SkillsBench

The following task directories map to `tasks/<task-id>/` at the recorded
SkillsBench revision:

- `citation-check`
- `econ-detrending-correlation`
- `lab-unit-harmonization`
- `pddl-tpp-planning`
- `sales-pivot-analysis`
- `virtualhome-agent-planning`
- `xlsx-recover-data`

The retained instructions, input artifacts, reference solutions and verifier
Python files match that revision. AgentMeter's local adaptations are package
mirror/runtime setup in the seven `environment/Dockerfile` files, dependency
bootstrap in four `tests/test.sh` files (`citation-check`,
`econ-detrending-correlation`, `pddl-tpp-planning`, `xlsx-recover-data`), and
build timeout in `lab-unit-harmonization/task.toml`. These modified files
carry an adaptation notice; the verifier Python code is unchanged.

Task-specific skill contents, including supporting scripts and references,
are not redistributed. Their [inventory](../integrations/skillsbench/SKILLS.md)
records the upstream paths and file hashes. The root SkillsBench license is
not treated as overriding a skill's separate terms.

## DA-Code

The `dm-csv-001`, `dm-csv-009` and `dm-csv-011` task definitions adapt the
DA-Code data-manipulation tasks to Harbor. Original task records are in
`da_code/configs/task/dm.jsonl` at the recorded revision. The local adapter adds
the container paths, package environment and verifier entry points. The
original DA-Code copyright and MIT license are retained.

## Terminal-Bench-compatible snapshots

The project identifies `async-task-scheduler`, `bash-script-debugger`,
`csv-data-validator`, `lru-cache-with-ttl`, `markdown-table-generator` and
`regex-log` as Terminal-Bench-derived tasks. This release retains the local
Harbor-compatible snapshots used by the study, not a claim of byte-identical
files from a particular official Terminal-Bench release.

## AgentMeter-Opt examples

The [four-source example catalog](../artifacts/agentmeter_opt_final16/README.md)
identifies each original task and its AgentMeter-authored adaptations.
`baseline_instruction.md` preserves the local Original; each
`optimized_instruction.md` is an AgentMeter-Opt modification, not an upstream
benchmark instruction. The applicable source terms above also cover retained
upstream text in these examples. Instructions are kept unchanged to preserve
the text evaluated in the study; attribution is provided here and in the
catalog rather than injected into the agent prompt.

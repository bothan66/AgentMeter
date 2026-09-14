# Final16 benchmark tasks

This directory freezes the 16 executable task bundles used by the
AgentMeter-Opt study. Each task retains its original `instruction.md`, Docker
environment, input artifacts, verifier, and reference solution so that Harbor
can execute it without a separate local task checkout.

| Subdirectory | Origin | Tasks |
|:--|:--|--:|
| `skillsbench/` | SkillsBench task collection | 7 |
| `terminal_bench/` | Terminal-Bench-compatible collection | 6 |
| `da_code/` | DA-Code-compatible collection | 3 |

The files are included for experiment reproducibility. AgentMeter does not
claim authorship of upstream task content. Consult the corresponding upstream
benchmark licenses before redistributing a derived task independently.

Optimized descriptions are stored separately under
`artifacts/agentmeter_opt_final16/descriptions/`; the immutable task bundles
here always contain the shared Original description.

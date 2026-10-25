# Final16 benchmark tasks

This directory freezes the 16 executable task bundles used by the
AgentMeter-Opt study. Each task retains its original `instruction.md`, Docker
environment, input artifacts, verifier, and reference solution. Third-party
skill contents are external dependencies rather than bundled source files.
For the seven SkillsBench tasks, prepare the files listed in the
[skill inventory](../integrations/skillsbench/SKILLS.md) before Harbor execution.

| Subdirectory | Origin | Tasks |
|:--|:--|--:|
| `skillsbench/` | SkillsBench task collection | 7 |
| `terminal_bench/` | Terminal-Bench-compatible collection | 6 |
| `da_code/` | DA-Code-compatible collection | 3 |

The files are included for experiment reproducibility. AgentMeter does not
claim authorship of upstream task content. [Sources and adaptations](SOURCES.md)
identify upstream revisions and the retained family-specific licenses.

Optimized descriptions are stored separately under
`artifacts/agentmeter_opt_final16/descriptions/`; the immutable task bundles
here always contain the shared Original description. Removing bundled skills
does not change the descriptions, Dockerfile skill paths, or verifier rules.

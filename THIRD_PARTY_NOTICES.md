# Third-party components

The root MIT license covers AgentMeter-authored code, not a relicensing of
third-party benchmark data or adapter code.

| Component | Source / terms | Release scope |
|:--|:--|:--|
| Harbor compatibility patch | laude-institute/harbor; Apache-2.0, copy in integrations/harbor/LICENSE | Four locally modified CLI adapters, base revision documented in docs/external_dependencies.md |
| Final16 task bundles | SkillsBench, Terminal-Bench-compatible and DA-Code-compatible local collections | Task-level original revision and redistribution notices still need reconciliation before public release |
| Bundled XLSX skill | `benchmark_tasks/skillsbench/xlsx-recover-data/environment/skills/xlsx/LICENSE.txt` | The included license expressly restricts copying and third-party distribution; establish applicable redistribution permission or exclude this material from a public artifact |
| Model and CLI providers | External services and software, under their own terms | Credentials and binaries not included |

Family names identify the local source collection; they are not proof of an
upstream revision or redistribution license. The bundled tasks are retained
for reproducibility review. Their per-task provenance and data licenses remain
an explicit public-release prerequisite.

The XLSX skill also exists in Git history. Removing it only from the latest
checkout would not remove it from a public repository's earlier commits.
Keep the current repository private while resolving the task-bundle terms.

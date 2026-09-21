# Third-party components

The root MIT license covers AgentMeter-authored code, not a relicensing of
third-party benchmark data or adapter code.

| Component | Source / terms | Release scope |
|:--|:--|:--|
| Harbor compatibility patch | laude-institute/harbor; Apache-2.0, copy in integrations/harbor/LICENSE | Four locally modified CLI adapters, base revision documented in docs/external_dependencies.md |
| Modified CLIProxyAPI source snapshot | router-for-me/CLIProxyAPI; MIT, retained in integrations/cliproxyapi/source/LICENSE | Source and regression tests, identified by source-manifest.json; original upstream commit unavailable in the local snapshot |
| Final16 task bundles | SkillsBench, Terminal-Bench-compatible and DA-Code-compatible local collections | Task-level original revision and redistribution notices still need reconciliation before public release |
| Selected Original/rewritten description pairs | Benchmark-derived Original text and AgentMeter-Opt modifications; [catalog and attribution](artifacts/agentmeter_opt_final16/README.md#provenance-and-reuse) | Retained as research examples. Original content keeps its applicable terms; modifications are identified in the catalog. Review the description's own provenance separately from bundled third-party skills |
| Bundled XLSX skill | `benchmark_tasks/skillsbench/xlsx-recover-data/environment/skills/xlsx/LICENSE.txt` | The included license expressly restricts copying and third-party distribution; establish applicable redistribution permission or exclude this material from a public artifact |
| Model and CLI providers | External services and software, under their own terms | Credentials and binaries not included |

Family names identify the local source collection; they are not proof of an
upstream revision or redistribution license. The bundled tasks are retained
for reproducibility review. Their per-task provenance and data licenses remain
an explicit public-release prerequisite.

The XLSX skill also exists in Git history. Removing it only from the latest
checkout would not remove it from a public repository's earlier commits.
Keep the current repository private while resolving the task-bundle terms.

This is not a blanket restriction on publishing AgentMeter's description
adaptations. For descriptions covered by a permissive upstream license,
retain the required license and notices and identify the modifications.
Do not infer the terms of a historical task solely from the current upstream
root license, or apply the XLSX skill's separate restrictions to unrelated
instruction text.

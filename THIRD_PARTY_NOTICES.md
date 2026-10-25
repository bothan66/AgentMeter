# Third-party components

The root MIT license covers AgentMeter-authored code, not a relicensing of
third-party benchmark data or adapter code.

| Component | Source / terms | Release scope |
|:--|:--|:--|
| Harbor compatibility patch | laude-institute/harbor; Apache-2.0, copy in integrations/harbor/LICENSE | Four locally modified CLI adapters, base revision documented in docs/external_dependencies.md |
| Modified CLIProxyAPI source snapshot | router-for-me/CLIProxyAPI; MIT, retained in integrations/cliproxyapi/source/LICENSE | Source and regression tests, identified by source-manifest.json; original upstream commit unavailable in the local snapshot |
| Final16 task bundles | [Sources, revisions and local adaptations](benchmark_tasks/SOURCES.md) | SkillsBench and Terminal-Bench material retain Apache-2.0; DA-Code material retains MIT. Source licenses are included in each family directory |
| Selected Original/rewritten description pairs | Benchmark-derived Original text and AgentMeter-Opt modifications; [catalog and attribution](artifacts/agentmeter_opt_final16/README.md#provenance-and-reuse) | Retained as research examples. Original content keeps its applicable terms; modifications are identified in the catalog. Review the description's own provenance separately from bundled third-party skills |
| External SkillsBench skills | [Task/skill inventory](integrations/skillsbench/SKILLS.md) and [file hashes](integrations/skillsbench/skills_manifest.json) | Skill contents are not included in the current release tree. Users supply dependencies separately under the applicable upstream terms; the preparation command does not grant redistribution rights |
| Model and CLI providers | External services and software, under their own terms | Credentials and binaries not included |

Task-level attribution and the distinction between upstream snapshots and
local Harbor adaptations are documented in [benchmark sources](benchmark_tasks/SOURCES.md).
All source authorship, copyright and separate notices remain applicable.
AgentMeter-Opt modifications are identified by the example catalog; its
`optimized_instruction.md` files must not be presented as upstream originals.

External skill contents must not be added back to this repository. Their own
terms apply independently of the benchmark's root license. The preparation
command verifies user-supplied dependencies without granting redistribution
rights. Provider accounts, model access and datasets remain subject to their
respective terms.

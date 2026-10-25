# SkillsBench skill dependencies

AgentMeter uses task-specific skills from the historical local
[SkillsBench](https://github.com/benchflow-ai/skillsbench) task collection.
Their contents are not bundled in the current release. This inventory records
which dependencies the seven SkillsBench task environments expect; it does
not claim that the agent read every available skill in each run.

Paths below are relative to `tasks/<task>/environment/skills/` in the source
collection. The machine-readable [manifest](skills_manifest.json) lists all
33 files, including supporting scripts and references, with SHA256 hashes.

| Task | Skill entry files |
|:--|:--|
| `citation-check` | `citation-management/SKILL.md` |
| `econ-detrending-correlation` | `timeseries-detrending/SKILL.md` |
| `lab-unit-harmonization` | `lab-unit-harmonization/SKILL.md` |
| `pddl-tpp-planning` | `pddl-skills/SKILL.md` |
| `sales-pivot-analysis` | `pdf/SKILL.md`, `xlsx/SKILL.md` |
| `virtualhome-agent-planning` | `pddl-skills/SKILL.md` |
| `xlsx-recover-data` | `data-reconciliation/SKILL.md`, `xlsx/SKILL.md` |

## Prepare for execution

Obtain the matching dependencies separately under their applicable terms.
From the AgentMeter checkout, point the helper to your source task collection:

```bash
# One example task; omit --task to prepare all seven tasks.
agentmeter prepare-skills --source-root /path/to/skillsbench/tasks \
  --task citation-check
```

The helper verifies every selected source file before copying, refuses changed
destination files, and places dependencies in Git-ignored
`benchmark_tasks/skillsbench/<task>/environment/skills/` directories. It does
not download, execute, translate, or replace skill content. The Harbor launcher
checks these dependencies before creating runs; missing skills are not silently
treated as a no-skill condition. A dry run only previews the execution plan.

The exact upstream commit corresponding to these historical skill files has
not been verified. The runtime lock's SkillsBench revision is a reference,
not a verified pin for these files; the recorded hashes identify their contents.
A different upstream version must not be substituted silently in a historical
replay. Identically named skills in different task directories can differ.

Paper-table reconstruction and tasks without these dependencies, including
the README's `dm-csv-009` example, need no skill preparation.

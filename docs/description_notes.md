# Reading the four-source task example

The release shows all four historical rewrites for `dm-csv-009` together,
rather than selecting different tasks for different sources. See the
[example catalog](../artifacts/agentmeter_opt_final16/README.md) for exact
instructions, all four paired results and replay commands.

## Shared public basis

The Original asks for the top 10 best-rated, most expensive and most-rated
authors. Its public
[guidance](../benchmark_tasks/da_code/dm-csv-009/environment/guidance.txt)
defines author-level aggregation, ranking metrics and the ratings threshold.
The public
[template](../benchmark_tasks/da_code/dm-csv-009/environment/sample_result.csv)
defines four columns and row IDs 0–9. Input files are under `/app/data/`;
the requested deliverable is `/app/output/author.csv`.

| Source rewrite | Change | Public grounding |
|:--|:--|:--|
| [DeepSeek × Kimi](../artifacts/agentmeter_opt_final16/descriptions/deepseek_v4_kimi_cli/dm-csv-009/) | Uses complete guidance, template and output paths. | Original file references and environment paths. |
| [GLM × Qwen](../artifacts/agentmeter_opt_final16/descriptions/glm51_qwen_coder/dm-csv-009/) | Names guidance criteria and lists the CSV columns and IDs. | Guidance, CSV template and bundled book data. |
| [Qwen × Codex](../artifacts/agentmeter_opt_final16/descriptions/qwen36_codex/dm-csv-009/) | States that guidance metrics and thresholds govern ranking; lists columns and rank IDs. | Guidance's top-10 rankings and the template's rows 0–9. |
| [Qwen × Kimi](../artifacts/agentmeter_opt_final16/descriptions/qwen36_kimi_cli/dm-csv-009/) | Explicitly requests reading the guidance and matching the template. | The same guidance and template named in Original. |

These edits clarify information available to the agent without replacing
the input data, output task or verifier. The historical descriptions are
preserved byte-for-byte; these notes do not revise evaluated instructions.

## Reading the paired outcomes

Three source-matched rewrites preserve partial reward while reducing
recorded cost. Qwen × Codex increases reward from 0 to 0.333 and also
increases cost. All four are displayed together; none is omitted based on
its outcome.

The complete archived study, not this illustrative task group, supplies the
paper's aggregate results. Public grounding lets readers inspect task
preservation, but is not by itself a proof of semantic equivalence.
Paired outcomes measure a full rewrite, not the causal contribution of one
sentence, and the four source pairs are different execution configurations.

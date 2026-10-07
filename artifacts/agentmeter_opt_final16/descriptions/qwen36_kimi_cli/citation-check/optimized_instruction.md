You are helping a research team verify the integrity of their bibliography before submitting a paper. The team suspects that some citations in their BibTeX file may be fake or hallucinated.

Your task is to identify which citations are fake or hallucinated and write the results to a JSON file.

### Input
- BibTeX file: `/root/test.bib`

### Output
Write your findings to `/root/answer.json` in the following exact format:

```json
{
  "fake_citations": [
    "Cleaned Title of First Fake Paper",
    "Cleaned Title of Second Fake Paper"
  ]
}
```

### Requirements
- Return only the **titles** of the fake citations in the `fake_citations` array.
- Titles must be cleaned (remove BibTeX formatting like `{}` or `\`).
- Sort the titles alphabetically for consistency.

### Completion Condition
- Once `/root/answer.json` has been successfully written, terminate your execution immediately. Do not output any further summaries, explanations, or conversational text.
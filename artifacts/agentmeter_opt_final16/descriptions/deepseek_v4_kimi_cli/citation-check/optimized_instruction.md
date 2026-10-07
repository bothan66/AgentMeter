You are helping a research team verify the integrity of their bibliography before submitting a paper. The team suspects that some citations in their BibTeX file may be fake or hallucinated.

## Input
- BibTeX file: `/root/test.bib` (contains a mix of real and potentially fake academic citations)

## Task
Identify which citations in the BibTeX file are fake or hallucinated.

## Output
Write your findings to `/root/answer.json` using the following JSON format:

```json
{
  "fake_citations": [
    "Title of first fake paper",
    "Title of second fake paper"
  ]
}
```

## Requirements
- Return only the **titles** of the fake citations in the `fake_citations` array.
- Clean the titles by removing BibTeX formatting (e.g., `{}`, `\`).
- Sort the titles alphabetically for consistency.
- Completion condition: Once `/root/answer.json` is written with the required output, your task is complete. Stop immediately without further verification, analysis, or tool calls.
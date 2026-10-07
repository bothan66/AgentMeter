You are helping a research team verify the integrity of their bibliography before submitting a paper. The team suspects that some citations in their BibTeX file may be fake or hallucinated.

## Input
- **BibTeX File**: `/root/test.bib` (contains a mix of real and potentially fake academic citations).

## Task
Identify which citations in the BibTeX file are fake or hallucinated.

## Output Requirements
Write your findings to `/root/answer.json` using the following exact JSON schema:

```json
{
  "fake_citations": [
    "Cleaned Title of First Fake Paper",
    "Cleaned Title of Second Fake Paper"
  ]
}
```

### Formatting Rules
- Return **only** the titles of the fake citations in the `fake_citations` array.
- Clean the titles by removing all BibTeX formatting (e.g., `{}`, `\`, or extra quotes).
- Sort the titles alphabetically for consistency.

## Completion Condition
Once `/root/answer.json` has been successfully written with the required JSON payload, your task is complete. Immediately stop all further verification, web searches, analysis, or processing.
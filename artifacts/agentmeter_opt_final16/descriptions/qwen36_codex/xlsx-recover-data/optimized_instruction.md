Recover missing values in the Excel file `nasa_budget_incomplete.xlsx`.

**Requirements:**
- Missing values are marked with the exact string `???`.
- Analyze the logical and mathematical relationships between sheets (e.g., row/column totals, subtotals, cross-sheet references) to compute the correct numeric values.
- Replace each `???` with its computed numeric value.
- Preserve all original sheet names, non-missing data, and cell formatting.

**Output Contract & Completion:**
- Save the recovered workbook as `nasa_budget_recovered.xlsx` in the current working directory.
- The output file must be a valid Excel workbook containing zero `???` strings.
- The task is complete immediately after `nasa_budget_recovered.xlsx` is successfully saved to disk. No additional verification steps, output summaries, or test scripts are required.
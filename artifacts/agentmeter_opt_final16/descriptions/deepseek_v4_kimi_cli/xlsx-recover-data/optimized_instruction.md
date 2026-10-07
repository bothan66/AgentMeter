Recover missing values in the Excel file `nasa_budget_incomplete.xlsx`. Missing values are marked with the exact string "???".

Analyze the relationships between the sheets to determine the correct values and replace each "???" with the computed numeric value. The workbook relies on the following cross-sheet relationships:
- **Budget by Directorate**: The "Total" column for each fiscal year is the exact sum of the individual directorate columns for that same year.
- **YoY (Year-over-Year)**: Values represent the percentage change from the previous fiscal year, calculated as `((Current Year Value - Previous Year Value) / Previous Year Value) * 100`. Note that the rows in the YoY sheet represent the transitions between consecutive fiscal years (e.g., the first row of YoY data corresponds to the percentage change from the first fiscal year to the second fiscal year).

Replace all "???" placeholders with the correct numeric values derived from these relationships. Preserve all original formatting, sheets, and non-missing data. Save the final workbook as `nasa_budget_recovered.xlsx`.
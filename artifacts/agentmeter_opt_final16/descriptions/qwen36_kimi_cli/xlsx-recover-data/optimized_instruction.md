Recover missing values in the Excel file `nasa_budget_incomplete.xlsx`. 

Missing values are marked with the exact string `"???"`. Analyze the mathematical relationships and constraints within and between sheets (such as row/column totals, year-over-year percentage changes, percentage shares, CAGR, and averages) to compute the correct values.

Replace every instance of `"???"` with its corresponding computed numeric value. Ensure the data type and scale match the context of the surrounding cells (e.g., use integers for absolute budget amounts, and match the percentage scale—such as `0.xx` versus `xx.xx`—used in adjacent cells). Preserve all unmodified data, sheets, and formatting.

Save the completed workbook as `nasa_budget_recovered.xlsx`. Verify that no `"???"` strings remain in any sheet of the final output.
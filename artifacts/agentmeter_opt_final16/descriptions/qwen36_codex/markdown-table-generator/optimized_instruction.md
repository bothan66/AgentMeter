Generate a Markdown sales report from the CSV file at `/app/data/sales_report.csv`.

The CSV has the following columns: `region`, `product`, `q1_sales`, `q2_sales`, `q3_sales`, `q4_sales`, `total`.

Write the Markdown report to `/app/output/report.md`. The report must contain **all three** of the following sections in the exact order and format specified below.

---

## 1. Summary Section

A section headed `## Summary` that states the grand total of sales (the sum of the `total` column across all rows).

**Required Format:**
```markdown
## Summary

Total sales across all regions: $X,XXX,XXX.XX
```
*Note: The monetary value must include a dollar sign (`$`), commas for thousands separators, and exactly two decimal places.*

---

## 2. Data Table

A section headed `## Sales by Region and Product` containing a properly formatted Markdown table of **all rows** from the CSV, sorted by the `total` column in **descending** order.

**Required Columns (in exact order):** `Region`, `Product`, `Q1`, `Q2`, `Q3`, `Q4`, `Total`.

**Table Formatting Rules:**
- Use `|` as the column separator and include a header separator row (e.g., `|---|---|...|`).
- Output the numeric values in the table exactly as they appear in the CSV (e.g., `145200`), without adding commas, dollar signs, or decimal places.

---

## 3. Top Performer Section

A section headed `## Top Performer` that identifies:
1. The **region** with the highest sum of `total` sales across all its products.
2. The **product** with the highest sum of `total` sales across all regions.

**Required Format:**
```markdown
## Top Performer

Top region: [Region Name] ($X,XXX,XXX.XX)
Top product: [Product Name] ($X,XXX,XXX.XX)
```
*Note: The monetary values must include a dollar sign (`$`), commas for thousands separators, and exactly two decimal places.*

---

**Execution Notes:**
- Ensure the `/app/output/` directory is created if it does not exist.
- The final `/app/output/report.md` file must contain only the Markdown content specified above, with no extra conversational text or code blocks wrapping the entire file.
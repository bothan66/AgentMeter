Generate a Markdown sales report from the CSV file at `/app/data/sales_report.csv`.

The CSV has the following columns: `region`, `product`, `q1_sales`, `q2_sales`, `q3_sales`, `q4_sales`, `total`.

Write the Markdown report to `/app/output/report.md`. Create the `/app/output/` directory if it does not exist. 

The report must contain **exactly three** sections in the following order, with no additional text, conversational filler, or extra sections:

### 1. Summary Section

A section headed `## Summary` that states the total sales across all regions and all products combined (the sum of the `total` column). 
Format the total as currency with a dollar sign, thousands separators, and two decimal places.

Example:
```markdown
## Summary

Total sales across all regions: $1,234,567.00
```

### 2. Data Table

A section headed `## Sales by Region and Product` containing a properly formatted Markdown table of **all rows** from the CSV, sorted by the `total` column in **descending** order.

The table must have these exact columns (in order): `Region`, `Product`, `Q1`, `Q2`, `Q3`, `Q4`, `Total`.
Format all numeric values in the table as currency with a dollar sign, thousands separators, and two decimal places (e.g., `$145,200.00`).

Use standard Markdown table format with `|` as the column separator and a header separator row (e.g., `|---|---|`).

### 3. Top Performer Section

A section headed `## Top Performer` that identifies:
- The **region** with the highest sum of `total` sales across all its products.
- The **product** with the highest sum of `total` sales across all regions.

Format the sales totals as currency with a dollar sign, thousands separators, and two decimal places.

Example:
```markdown
## Top Performer

Top region: North America ($456,789.00)
Top product: Widget Pro ($234,567.00)
```
Generate a Markdown sales report from the CSV file at `/app/data/sales_report.csv`.

The CSV has the following columns: `region`, `product`, `q1_sales`, `q2_sales`, `q3_sales`, `q4_sales`, `total`.

Write the Markdown report to `/app/output/report.md`. The report must contain **all three** of the following sections:

---

## 1. Summary Section

A section headed `## Summary` that states the total sales across all regions and all products combined (sum of the `total` column).

Example:
```
## Summary

Total sales across all regions: $1,234,567.00
```

---

## 2. Data Table

A section headed `## Sales by Region and Product` containing a properly formatted Markdown table of **all rows** from the CSV, sorted by `total` **descending**.

The table must have these columns (in order): `Region`, `Product`, `Q1`, `Q2`, `Q3`, `Q4`, `Total`.

Markdown table format uses `|` as a column separator and a header separator row like `|---|---|...|`.

---

## 3. Top Performer Section

A section headed `## Top Performer` that identifies:
- The **region** with the highest sum of `total` sales across all its products
- The **product** with the highest sum of `total` sales across all regions

Example:
```
## Top Performer

Top region: North America ($456,789.00)
Top product: Widget Pro ($234,567.00)
```

---

Note: `/app/output/` directory may need to be created.

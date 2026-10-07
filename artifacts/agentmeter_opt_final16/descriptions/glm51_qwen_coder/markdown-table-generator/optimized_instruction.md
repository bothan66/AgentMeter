Generate a Markdown sales report from the CSV file at `/app/data/sales_report.csv`.

The CSV has the following columns: `region`, `product`, `q1_sales`, `q2_sales`, `q3_sales`, `q4_sales`, `total`.

Write the Markdown report to `/app/output/report.md`. Create the `/app/output/` directory if it does not exist.

The report must contain **exactly** the following three sections, in this order, with no extra text, introductions, or conclusions outside these sections:

## Summary

Total sales across all regions: $<TOTAL_SALES>

## Sales by Region and Product

| Region | Product | Q1 | Q2 | Q3 | Q4 | Total |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... |

## Top Performer

Top region: <TOP_REGION> ($<REGION_SALES>)
Top product: <TOP_PRODUCT> ($<PRODUCT_SALES>)

### Formatting and Content Rules:

1. **Monetary Values**: In the Summary and Top Performer sections, format all sales figures with a dollar sign, thousands separators, and exactly two decimal places (e.g., `$1,234,567.00`).
2. **Data Table**: 
   - Include **all rows** from the CSV.
   - Sort the rows by the `Total` column in **descending** order.
   - Use the exact column headers: `Region`, `Product`, `Q1`, `Q2`, `Q3`, `Q4`, `Total`.
   - Use standard Markdown table syntax with `|` separators and a `|---|` header separator row.
3. **Top Performer**:
   - `<TOP_REGION>` is the region with the highest sum of `total` sales across all its products.
   - `<TOP_PRODUCT>` is the product with the highest sum of `total` sales across all regions.
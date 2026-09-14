#!/bin/bash
# Solution: generate a Markdown sales report from CSV data

export PATH="/root/.local/bin:$PATH"
cd /app

uv venv .tbench-solve 2>/dev/null
source .tbench-solve/bin/activate
uv pip install pandas==2.2.0

mkdir -p /app/output

python3 - <<'PYEOF'
import pandas as pd
import os

CSV_PATH = "/app/data/sales_report.csv"
OUTPUT_PATH = "/app/output/report.md"

df = pd.read_csv(CSV_PATH)

# --- Summary ---
grand_total = df["total"].sum()

# --- Sort by total descending ---
df_sorted = df.sort_values("total", ascending=False).reset_index(drop=True)

# --- Build Markdown table ---
def fmt(n):
    return f"{n:,.0f}"

header = "| Region | Product | Q1 | Q2 | Q3 | Q4 | Total |"
sep    = "|--------|---------|----|----|----|----|-------|"
rows = []
for _, r in df_sorted.iterrows():
    rows.append(
        f"| {r['region']} | {r['product']} | "
        f"{fmt(r['q1_sales'])} | {fmt(r['q2_sales'])} | "
        f"{fmt(r['q3_sales'])} | {fmt(r['q4_sales'])} | "
        f"{fmt(r['total'])} |"
    )

table_section = "\n".join([header, sep] + rows)

# --- Top performers ---
region_totals = df.groupby("region")["total"].sum()
top_region = region_totals.idxmax()
top_region_total = region_totals.max()

product_totals = df.groupby("product")["total"].sum()
top_product = product_totals.idxmax()
top_product_total = product_totals.max()

# --- Assemble report ---
report = f"""# Sales Report

## Summary

Total sales across all regions: ${grand_total:,.2f}

## Sales by Region and Product

{table_section}

## Top Performer

Top region: {top_region} (${top_region_total:,.2f})
Top product: {top_product} (${top_product_total:,.2f})
"""

with open(OUTPUT_PATH, "w") as f:
    f.write(report)

print(f"Report written to {OUTPUT_PATH}")
print(f"Grand total: ${grand_total:,.2f}")
print(f"Top region: {top_region}")
print(f"Top product: {top_product}")
PYEOF

Read the population data from `/root/population.pdf` and the income data from `/root/income.xlsx`. Merge the datasets and create a new Excel report saved as `/root/demographic_analysis.xlsx`.

The output Excel file must contain exactly five sheets with the following names and structures:

1. "Population by State"
This sheet contains a pivot table with the following structure:
- Rows: STATE
- Values: Sum of POPULATION_2023 (the population column extracted from the PDF)

2. "Earners by State"
This sheet contains a pivot table with the following structure:
- Rows: STATE
- Values: Sum of EARNERS

3. "Regions by State"
This sheet contains a pivot table with the following structure:
- Rows: STATE
- Values: Count of SA2 regions (count of the unique region identifiers)

4. "State Income Quartile"
This sheet contains a pivot table with the following structure:
- Rows: STATE
- Columns: Quarter. Categorize all regions into four quartiles named "Q1", "Q2", "Q3", and "Q4" based on the distribution of their MEDIAN_INCOME values.
- Values: Sum of EARNERS

5. "SourceData"
This sheet contains a regular table with the merged original data from both sources, enriched with the following new columns:
- Quarter: The income quartile for each region ("Q1", "Q2", "Q3", or "Q4"), based on the region's MEDIAN_INCOME.
- Total: The product of EARNERS and MEDIAN_INCOME (EARNERS × MEDIAN_INCOME).

Save the final results in `/root/demographic_analysis.xlsx`. The task is complete when this file is successfully generated with all five correctly structured sheets.
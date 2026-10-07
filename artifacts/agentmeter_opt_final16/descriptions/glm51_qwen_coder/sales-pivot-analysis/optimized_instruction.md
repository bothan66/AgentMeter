Read the population data from `/root/population.pdf` and the income data from `/root/income.xlsx`, merge them, and create a new report called `/root/demographic_analysis.xlsx`.

### Input Data Schema
- **Population PDF (`/root/population.pdf`)**: Contains a multi-page table with exactly four columns: `SA2_CODE`, `SA2_NAME`, `STATE`, and `POPULATION_2023`. Note that the table spans multiple pages and column headers may repeat on each page.
- **Income Excel (`/root/income.xlsx`)**: Contains a sheet with the columns: `SA2_CODE`, `SA2_NAME`, `EARNERS`, `MEDIAN_INCOME`, and `MEAN_INCOME`.

Merge the two datasets using `SA2_CODE` as the primary key.

### Output Requirements
The new Excel file must contain exactly five sheets, structured as follows:

1. **"Population by State"**
   A pivot table with:
   - Rows: `STATE`
   - Values: Sum of `POPULATION_2023`

2. **"Earners by State"**
   A pivot table with:
   - Rows: `STATE`
   - Values: Sum of `EARNERS`

3. **"Regions by State"**
   A pivot table with:
   - Rows: `STATE`
   - Values: Count of `SA2_CODE` (representing the number of SA2 regions)

4. **"State Income Quartile"**
   A pivot table with:
   - Rows: `STATE`
   - Columns: `Quarter` (Use the exact terms "Q1", "Q2", "Q3", and "Q4")
   - Values: Sum of `EARNERS`
   *Note: Determine the quartiles based on the distribution of `MEDIAN_INCOME` across all regions in the merged dataset.*

5. **"SourceData"**
   A regular table containing the merged dataset, enriched with the following calculated columns:
   - `Quarter`: Assign "Q1", "Q2", "Q3", or "Q4" based on the `MEDIAN_INCOME` quartile range for each region.
   - `Total`: Calculated as `EARNERS` × `MEDIAN_INCOME`.

Save the final results in `/root/demographic_analysis.xlsx`.
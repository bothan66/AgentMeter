# dm-csv-009

**Type**: Data Manipulation
**Difficulty**: Hard

## Task

Identify the top 10 best-rated authors, the most expensive authors, and the authors with the most ratings. 

Follow the specific ranking, aggregation, and filtering criteria detailed in `guidance.txt`. 

Save the results to `author.csv`. The output must strictly follow the schema and format provided in `sample_result.csv`, which includes the following columns:
- `id`: Row index (0 to 9).
- `Best-Rated Author`: Name of the author.
- `Most Expensive Author`: Name of the author.
- `Most Rated Author`: Name of the author.

## Environment

- Input data files (including `Books_df.csv`, `guidance.txt`, and `sample_result.csv`) are located in `/app/data/`.
- Save your output file to `/app/output/` with the exact filename: `author.csv`.
- Python packages available: pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib.
# dm-csv-009

**Type**: Data Manipulation
**Difficulty**: Hard

## Task

Identify the top 10 best-rated authors, the most expensive authors, and the authors with the most ratings. 

You must strictly follow the ranking criteria, metrics, and thresholds defined in `/app/data/guidance.txt`. 

Save the final results to `/app/output/author.csv`. The output file must exactly match the schema and format demonstrated in `/app/data/sample_result.csv`. The required columns are `id`, `Best-Rated Author`, `Most Expensive Author`, and `Most Rated Author`. The `id` column should contain integers from 0 to 9 representing the rank (0 being the highest).

## Environment

- Input data files are in `/app/data/`
- Save your output file(s) to `/app/output/` with the exact filename(s): `author.csv`
- Python packages available: pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib
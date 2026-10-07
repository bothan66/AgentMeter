A CSV file at `/app/data/employees.csv` contains employee records with the following columns:
`employee_id, name, email, department, salary, hire_date, manager_id`

The file has approximately 50 data rows (excluding the header). Some rows contain deliberate data-quality errors.

### Validation Rules

| Column | Rule |
|---|---|
| `employee_id` | Must be an integer; must be unique across all rows |
| `email` | Must match the pattern `*@*.*` (contains exactly one `@` and at least one `.` after the `@`) |
| `salary` | Must be a number strictly between 1000 and 500000 (exclusive) |
| `hire_date` | Must be a valid date in `YYYY-MM-DD` format; must not be after `2024-01-01` |
| `manager_id` | If not empty, must reference an `employee_id` that exists in the file |

### Task Requirements

1. Write a Python script at `/app/validate.py`.
2. The script must read `/app/data/employees.csv`, apply the validation rules, and write the results to `/app/output/validation_report.json`.
3. Create the `/app/output/` directory if it does not exist.
4. Run the script using `python /app/validate.py`.

### Output JSON Schema

The output file `/app/output/validation_report.json` must strictly follow this structure:
```json
{
  "total_rows": 50,
  "valid_rows": 42,
  "errors": [
    {"row": 5,  "column": "email",       "error": "invalid email format", "value": "bademail"},
    {"row": 12, "column": "salary",      "error": "salary out of range",  "value": "999"}
  ]
}
```

- `total_rows`: Total count of data rows.
- `valid_rows`: Count of rows with zero errors.
- `errors`: A list of error objects. A row with multiple errors produces multiple entries.
- `row`: 1-based index (row 1 is the first data row after the header).

### Completion Condition
Your task is complete once the script executes successfully and the JSON report is written. Stop immediately. Do not read the output file back, do not verify the contents manually, and do not output any summaries or explanations.
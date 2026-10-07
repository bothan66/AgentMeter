A CSV file at `/app/data/employees.csv` contains employee records with the
following columns:

```
employee_id, name, email, department, salary, hire_date, manager_id
```

The file has approximately 50 data rows (excluding the header). Some rows
contain deliberate data-quality errors.

### Validation rules

| Column | Rule |
|---|---|
| `employee_id` | Must be an integer; must be unique across all rows |
| `email` | Must match the pattern `*@*.*` (contains exactly one `@` and at least one `.` after the `@`) |
| `salary` | Must be a number strictly between 1 000 and 500 000 (exclusive) |
| `hire_date` | Must be a valid date in `YYYY-MM-DD` format; must not be after `2024-01-01` |
| `manager_id` | If not empty, must reference an `employee_id` that exists in the file |

### Your task

Write `/app/validate.py` that reads `/app/data/employees.csv`, applies
the rules above, and writes `/app/output/validation_report.json`:

```json
{
  "total_rows": 50,
  "valid_rows": 42,
  "errors": [
    {"row": 5,  "column": "email",       "error": "invalid email format", "value": "bademail"},
    {"row": 12, "column": "salary",      "error": "salary out of range",  "value": "999"},
    ...
  ]
}
```

- `row` is 1-based (row 1 = first data row after the header).
- A row with multiple errors produces multiple entries in `errors`.
- `valid_rows` = rows with zero errors.
- Create `/app/output/` if it does not exist.

Run with `python /app/validate.py`.

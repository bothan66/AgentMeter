Solve tasks using PDDL (Planning Domain Definition Language). These planning tasks are taken from the problem suites of the International Planning Competitions (IPC). Planners control the ground traffic on airports. The largest instances in the test suites are realistic encodings of Munich airport.

Each task has two input files: a PDDL domain file and a PDDL problem file. The domain and problem file paths for each task are specified by the "domain" and "problem" keys in the `problem.json` file. An example task entry looks like this:

```json
[
  {
    "id": "problem_id",
    "domain": ".../xxx.pddl",
    "problem": ".../yyy.pddl",
    "plan_output": "xxx/problem_id.txt"
  }
]
```

For each task specified in `problem.json`, you must:
1. Load the PDDL domain file and PDDL problem file.
2. Generate a valid PDDL plan that solves the planning problem.
3. Write the generated plan to the exact path specified by the `plan_output` key.

An example of a correctly formatted PDDL plan output:

```text
drive(truck1, depot1, market1)
buy(truck1, goods1, market1, level0, level1, level0, level1)
load(goods1, truck1, market1, level0, level1, level0, level1)
drive(truck1, market1, depot1)
unload(goods1, truck1, depot1, level0, level1, level0, level1)
```

### Output Format Requirements
- **Strict Line Format**: Each action primitive must be written on its own line. 
- **No Prefixes**: Do not include line numbers, step numbers, timestamps, indices, or any other prefixes. Each line must contain *only* the action name and its arguments in parentheses (e.g., `drive(truck1, depot1, market1)`, NOT `1 drive(...)` or `0: drive(...)`).
- **Syntax and Validity**: The plan must be syntactically correct and valid according to the PDDL grammar, successfully solving the problem.
- **Name Matching**: Action names and object names in the generated plan must exactly match those defined in the PDDL domain and problem files.
- **Completeness**: You must generate and save the plan for every task listed in `problem.json`.
Solve tasks using PDDL (Planning Domain Definition Language). These planning tasks are taken from the problem suites of the International Planning Competitions (IPC). Planners control the ground traffic on airports. The largest instances in the test suites are realistic encodings of Munich airport.

## Input Files
The task list is specified in the `problem.json` file. Each task entry contains the paths to the PDDL domain file, the PDDL problem file, and the required output path for the plan. 

Example `problem.json` entry:
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

## Task Instructions
For each task specified in `problem.json`:
1. Load the PDDL domain file and PDDL problem file.
2. Generate a valid PDDL plan that solves the planning problem.
3. Write the generated plan to the exact path specified by the `plan_output` key.

## Output Format
The generated plan must be a syntactically correct and valid PDDL plan. The output file must strictly adhere to the following format:
- Each action primitive must be written on a separate line.
- Action names and object names must exactly match the PDDL domain and problem definitions.
- Do not include step numbers, timestamps, costs, or any extra text/comments. Only output the raw action primitives.

Example PDDL plan output:
```text
drive(truck1, depot1, market1)
buy(truck1, goods1, market1, level0, level1, level0, level1)
load(goods1, truck1, market1, level0, level1, level0, level1)
drive(truck1, market1, depot1)
unload(goods1, truck1, depot1, level0, level1, level0, level1)
```

## Completion Condition
Your task is complete once all required `plan_output` files have been successfully written to disk. Stop immediately after generating and saving the final plan file; do not perform additional validation loops or read the output files back.
The script at `/app/scripts/deploy.sh` is a deployment helper that has **exactly 5 bugs**. Your job is to find and fix all of them.

The script is supposed to:

1. Accept a single argument: the path to a config file.
2. Verify that the config file exists; exit with code 1 and a clear error message if it does not.
3. Source (load) the config file to import environment variables.
4. Create the deployment directories `/app/deploy/releases` and `/app/deploy/logs` (including any missing parent directories).
5. Set permissions `755` on `/app/deploy`.
6. Write a timestamped log entry to `/app/deploy/logs/deploy.log`.
7. Print `"Deployment successful"` to stdout and exit with code 0.

### What to submit

Save the **corrected** script to `/app/scripts/deploy_fixed.sh` and make it executable (`chmod +x`).

Do **not** change the overall logic or structure of the script beyond fixing the 5 bugs. Each bug is a single-line mistake.

### Hint – categories of bugs present

- A variable used without being quoted (causes word-splitting on paths with spaces)
- `mkdir` called without the flag needed to create parent directories
- A file-existence test using the wrong operator
- An arithmetic/string comparison using the wrong operator inside `[[ ]]`
- A missing `export` for a variable that must be visible to child processes

### Testing your fix

```bash
echo 'APP_VERSION=1.2.3' > /tmp/test.conf
bash /app/scripts/deploy_fixed.sh /tmp/test.conf
# Should print: Deployment successful
# Should exit 0
```

### Completion Condition

Once the fixed script is saved, made executable, and successfully verified with the test command, your task is complete. Stop immediately and do not output any summaries, explanations, or tables of the bugs fixed.
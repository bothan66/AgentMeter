# Unified CLI Gateway

This is the renamed integration layer for the user's modified CLIProxyAPI-style gateway.

The harness does not vendor private gateway code or configuration. It expects a HTTP API that accepts:

```json
{
  "task_id": "organize-messy-files",
  "model": "anthropic_model",
  "cli": "anthropic_cli",
  "task_dir": "/abs/path/to/attempt/task",
  "run_dir": "/abs/path/to/attempt",
  "timeout_sec": 900
}
```

Supported response formats:

- `anthropic`
- `responses`
- `completions`
- `agentmeter`

Configure each model/CLI pair in `configs/runners.local.yaml`:

```yaml
api_runners:
  model_a__cli_a:
    url: "https://your-gateway.example/v1/run"
    method: POST
    api_key_env: AGENTMETER_API_KEY
    auth_header: Authorization
    auth_scheme: Bearer
    response_format: anthropic
    payload:
      task_id: "{task_id}"
      model: "{model}"
      cli: "{cli}"
      task_dir: "{task_dir}"
      run_dir: "{run_dir}"
      timeout_sec: "{timeout_sec}"
```

Adapter lookup order:

```text
model__cli
model.cli
cli
default
```

Secrets stay in environment variables and are not written to artifacts.

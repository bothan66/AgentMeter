# Unified CLI API Gateway

This harness supports a renamed, generic CLI API gateway instead of a hard-coded private CLIProxyAPI implementation.

Your gateway can expose any of these response formats:

- `agentmeter`: already-normalized benchmark response.
- `anthropic`: Anthropic Messages-style response.
- `responses`: OpenAI Responses-style response.
- `completions`: OpenAI-compatible Chat Completions or Completions response.

Set the format per model/CLI adapter in `configs/runners.local.yaml`:

```yaml
api_runners:
  model_a__cli_a:
    url: "https://your-gateway.example/v1/responses"
    method: POST
    api_key_env: AGENTMETER_API_KEY
    auth_header: Authorization
    auth_scheme: Bearer
    response_format: responses
    payload:
      model: "{model}"
      task_id: "{task_id}"
      cli: "{cli}"
      task_dir: "{task_dir}"
      run_dir: "{run_dir}"
      timeout_sec: "{timeout_sec}"
```

## Adapter Lookup

The runner chooses adapters in this order:

```text
model__cli
model.cli
cli
default
```

Use `model__cli` when a model/CLI pair needs special prompt wrapping, request body fields, model routing, or response parsing.

## Normalized Output

Regardless of gateway response format, each attempt writes:

```text
summary.json
usage.json
trajectory.jsonl
stdout.txt
stderr.txt
eval_result.json
patch.diff
run_meta.json
```

The normalized `summary.json` contains:

```json
{
  "passed": true,
  "input_tokens": 1000,
  "output_tokens": 200,
  "cache_read_tokens": 0,
  "cache_creation_tokens": 0,
  "cache_hit_tokens": 0,
  "total_tokens": 1200,
  "total_cost_cny": 0.0,
  "turns": 0,
  "tool_calls": 0,
  "exit_code": 0
}
```

## Supported Usage Fields

Anthropic:

```json
{
  "usage": {
    "input_tokens": 1000,
    "output_tokens": 200,
    "cache_creation_input_tokens": 120,
    "cache_read_input_tokens": 50
  }
}
```

Normalized cache fields:

```text
cache_creation_tokens = usage.cache_creation_input_tokens
cache_hit_tokens = usage.cache_read_input_tokens
cache_read_tokens = usage.cache_read_input_tokens
```

Responses:

```json
{
  "usage": {
    "input_tokens": 1000,
    "output_tokens": 200,
    "total_tokens": 1200,
    "input_token_details": {
      "cached_tokens": 80
    }
  }
}
```

Normalized cache fields:

```text
cache_creation_tokens = 0
cache_hit_tokens = usage.input_token_details.cached_tokens
cache_read_tokens = usage.input_token_details.cached_tokens
```

Completions:

```json
{
  "usage": {
    "prompt_tokens": 1000,
    "completion_tokens": 200,
    "total_tokens": 1200,
    "prompt_tokens_details": {
      "cached_tokens": 80
    }
  }
}
```

Normalized cache fields:

```text
cache_creation_tokens = 0
cache_hit_tokens = usage.prompt_tokens_details.cached_tokens
cache_read_tokens = usage.prompt_tokens_details.cached_tokens
```

AgentMeter-normalized:

```json
{
  "summary": {
    "passed": true,
    "input_tokens": 1000,
    "output_tokens": 200,
    "cache_read_tokens": 0,
    "cache_creation_tokens": 0,
    "cache_hit_tokens": 0,
    "total_tokens": 1200,
    "turns": 6,
    "tool_calls": 9
  },
  "trajectory_events": [
    {"type": "usage", "input_tokens": 1000, "output_tokens": 200, "cache_read_tokens": 0, "cache_creation_tokens": 0, "cache_hit_tokens": 0}
  ]
}
```

## Security

Real keys stay in environment variables:

```bash
export AGENTMETER_API_KEY="..."
```

The harness sends the key in the configured request header but does not write headers or environment variables to run artifacts.

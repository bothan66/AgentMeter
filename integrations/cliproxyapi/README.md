# AgentMeter's CLIProxyAPI snapshot

This directory includes the modified proxy source used for AgentMeter's
execution integration, with its upstream MIT license. Build from `source/`
to reproduce this snapshot's routing behavior. The original local copy had
no usable Git history, so `source-manifest.json` identifies the snapshot by
file hashes rather than an inferred upstream commit. This snapshot is not
a claim that every historical paper run used exactly this revision.

## Build

Use Go 1.26.0. From the AgentMeter repository root:

```bash
mkdir -p build/cliproxyapi
go -C integrations/cliproxyapi/source build -mod=readonly \
  -o ../../../build/cliproxyapi/cli-proxy-api ./cmd/server
```

Keep Go build/module caches on your data disk if needed (`GOCACHE`,
`GOMODCACHE`, `GOTMPDIR`). Dependencies are recorded in `go.mod` and `go.sum`.

## Configure a paper model

The example below exposes the paper's Qwen3.6-Plus × Codex combination.
Use the actual upstream model ID offered by your provider.

```bash
export AGENTMETER_PROXY_CLIENT_KEY=your-local-proxy-key
export UPSTREAM_OPENAI_API_KEY=your-upstream-key
export UPSTREAM_OPENAI_BASE_URL=https://your-provider.example/v1

agentmeter proxy-config \
  --host 0.0.0.0 --port 8317 \
  --model 'Qwen3.6+=YOUR_UPSTREAM_QWEN_MODEL_ID' \
  --output build/cliproxyapi/config.local.yaml

build/cliproxyapi/cli-proxy-api \
  --config build/cliproxyapi/config.local.yaml --local-model
```

Keep this process running and launch experiments in another terminal.
The renderer writes literal credential values with file mode 0600 and
refuses to overwrite an existing config. YAML `${...}` placeholders are
not assumed to expand automatically. Bind to a trusted interface reachable
from the task containers; requests require the configured client key.
Generated configs, `.env` files, OAuth data, logs, and compiled binaries are
ignored by Git. Do not force-add these private runtime files to a commit.

Repeat `--model CLIENT_ALIAS=UPSTREAM_ID` for additional models, for example
`deepseek-v4-pro=YOUR_DS_ID`, `glm-5.1=YOUR_GLM_ID`, or
`qwen3.7-max=YOUR_REFLECTION_ID`. The provided configuration generator
targets an upstream Chat Completions endpoint. Native Claude or other
provider credentials require their corresponding upstream configuration.

Use `--strip-unsupported-params` only for upstreams requiring that adaptation.
Use `--inject-prompt-cache` only when the upstream supports explicit cache
control. Both switches apply to the generated provider route and default to
off; record their settings with experiments. Changing these switches is not
a reconstruction of historical per-provider settings.

## Connect Harbor and Opt

For the host-side API probe:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8317/v1
export OPENAI_API_KEY="$AGENTMETER_PROXY_CLIENT_KEY"
export AGENTMETER_MODEL='Qwen3.6+'
agentmeter probe
```

Before running Harbor, replace the loopback host in `OPENAI_BASE_URL` with
the proxy host address reachable from Harbor's task network. Confirm
connectivity from that network; the default Docker bridge gateway is not
necessarily the gateway of a task's own network.

```bash
export OPENAI_BASE_URL=http://YOUR_DOCKER_REACHABLE_HOST:8317/v1
export AGENTMETER_AGENT=codex
export AGENTMETER_AGENT_VERSION=0.153.0
export CODEX_FORCE_API_KEY=1
export CODEX_WIRE_API=responses
agentmeter compare qwen36_codex original regex-log
```

The proxy exposes `/v1/responses`, `/v1/chat/completions`, and
`/v1/messages`. For Claude Code use the base `http://HOST:8317` in
`ANTHROPIC_BASE_URL` and the proxy client key in `ANTHROPIC_API_KEY`.
For host-side Opt reflection, use `OPENAI_BASE_URL=http://127.0.0.1:8317/v1`,
the client key, and `--reflection-model openai/qwen3.7-max` after registering
that alias. Kimi/Qwen clients must likewise use their configured provider
base URL and the client-facing alias. `AGENTMETER_GATEWAY_BASE_URL` is not
a launcher configuration variable.

## Included behavior and verification

The source includes model alias routing and protocol translation, configurable
unsupported-parameter removal and cache-control injection, and cache accounting
regressions covering cache misses, reads/writes, missing usage, and reasoning
token double counting. These describe this snapshot's behavior; they are not
an exhaustive attribution of changes against an unavailable upstream baseline.

```bash
go -C integrations/cliproxyapi/source test -mod=readonly \
  ./internal/runtime/executor/helps \
  ./internal/translator/openai/openai/responses ./internal/config
python tests/check_proxy_routes.py --binary build/cliproxyapi/cli-proxy-api
```

The route check starts an isolated proxy and local fixture upstream and tests
authentication, model alias mapping, and streaming/non-streaming protocol
routes without paid model calls. It does not validate a provider's availability,
pricing, or full agent execution. Raw configs, OAuth data, logs and compiled
binaries are not part of the source snapshot.

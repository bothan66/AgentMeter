# Execution dependencies

Final16 task bundles are included. Core30 and Full80 currently ship selections
only; a task checkout containing every selected ID is required.

## Harbor

Use Python 3.12 or 3.13 for the combined Harbor and Opt environment. The
pinned Harbor revision requires Python >=3.12; Python 3.11 supports only
AgentMeter's scoring package and Opt dependencies without this Harbor version.

The locally used Harbor base revision is
`07fa4c80c0e729a4ec0cc3184e93a6d730024f81`.
The four modified CLI adapters are preserved in
[`agentmeter_cli_adapters.patch`](../integrations/harbor/agentmeter_cli_adapters.patch), relative
to that revision. This is an execution compatibility snapshot, not a claim
that all historical paper runs used this exact runtime.

From an activated Python 3.12–3.13 environment at the AgentMeter repository root:

```bash
agentmeter setup
export AGENTMETER_HARBOR_BIN=harbor
```

The setup command prepares Harbor only. The 16 released task bundles are already
included. For larger Core30/Full80 selections, keep a separate compatible task
checkout outside this repository and set `AGENTMETER_TASK_ROOT` to it. Exact
dependency and task-source pins are machine-readable in
[`integrations/agentmeter_runtime.lock.json`](../integrations/agentmeter_runtime.lock.json).

The patch includes provider configuration for Codex, cache usage fields, and
CLI installation support. It retains historical npm mirror settings and the
Qwen cache-control modification. These affect the execution configuration and
must be reported when comparing against stock harnesses. Optional
`/opt/agent-runtime` preinstalled binaries are used when available; otherwise
the adapters install dependencies over the network. A mounted runtime can
override the requested CLI version: check the recorded version.

Docker must be installed and accessible to the invoking user. Building task
images requires registry and package-index access. Harbor installs the target
CLI inside each task container. Set `AGENTMETER_AGENT_VERSION` to pin its
version; leaving it unset uses Harbor's default and is not version-frozen.

## Provider routing

The provider-auth patch explicitly configures `env_key = "OPENAI_API_KEY"`
for the custom Codex provider. Without this setting, a reachable endpoint
can reject requests because no bearer credential was sent. See the
[official configuration reference](https://developers.openai.com/codex/config-reference/).

The same patch preserves full provider model IDs for custom endpoints.
For a Chat Completions upstream, `agentmeter proxy-config` generates a private
CLIProxyAPI route with explicit client aliases and provider model IDs. The
[proxy guide](../integrations/cliproxyapi/README.md) uses the paper's
Qwen3.6-Plus configuration.

Set `OPENAI_BASE_URL` to the proxy's `/v1` address and `OPENAI_API_KEY` to
the proxy's client key, then run `agentmeter probe` before
launching a task. From a task container, use a host address reachable from
that container rather than `127.0.0.1`. Host-only probes and container
execution may therefore need different base URLs. The proxy must listen
on the selected interface and permit connections from the task network;
a successful host probe alone does not verify container reachability.

Supply credentials via environment variables. Copying `.env.example` does
not load it automatically: export the values in your shell.
The Codex reproduction example uses a provider implementing Responses.
Other harnesses need their corresponding provider protocol and credentials.
CLIProxyAPI is optional. The modified source snapshot, configuration renderer,
build and startup commands are included under
[`integrations/cliproxyapi/`](../integrations/cliproxyapi/README.md).

## Storage and records

Set `AGENTMETER_JOBS_DIR` to a new output directory on a disk with sufficient
space. Final16 snapshots are retained there alongside job outputs so the
evaluated instruction remains inspectable. Set `TMPDIR` for host temporary
files. Docker/containerd storage is configured separately by the administrator;
changing these variables does not move image layers.

Archive the task revision, CLI version, provider model ID, generation settings,
timeouts, pricing date, cache accounting, and execution patch with each study.
API model revisions and nondeterminism can prevent exact replay of old scores.

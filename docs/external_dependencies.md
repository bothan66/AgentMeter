# Execution dependencies

Final16 task bundles are included. Core30 and Full80 currently ship selections
only; a task checkout containing every selected ID is required.

## Harbor

The locally used Harbor base revision is
`07fa4c80c0e729a4ec0cc3184e93a6d730024f81`.
The four modified CLI adapters are preserved in
[`compatibility.patch`](../integrations/harbor/compatibility.patch), relative
to that revision. This is an execution compatibility snapshot, not a claim
that all historical paper runs used this exact runtime.

From the AgentMeter repository root:

```bash
git clone https://github.com/laude-institute/harbor.git vendor/harbor
git -C vendor/harbor checkout 07fa4c80c0e729a4ec0cc3184e93a6d730024f81
git -C vendor/harbor apply --check ../../integrations/harbor/compatibility.patch
git -C vendor/harbor apply ../../integrations/harbor/compatibility.patch
python -m pip install -e vendor/harbor
export AGENTMETER_HARBOR_BIN=harbor
```

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

Supply credentials via environment variables. Copying `.env.example` does
not load it automatically: export the values in your shell.
The Codex reproduction example uses a provider implementing Responses.
Other harnesses need their corresponding provider protocol and credentials.
The local mock gateway is a development fixture, not a general production
protocol converter. CLIProxyAPI is optional; the configuration template under
`integrations/cliproxyapi/` does not include its implementation.

## Storage and records

Set `AGENTMETER_JOBS_DIR` to a new output directory on a disk with sufficient
space. Final16 snapshots are retained there alongside job outputs so the
evaluated instruction remains inspectable. Set `TMPDIR` for host temporary
files. Docker/containerd storage is configured separately by the administrator;
changing these variables does not move image layers.

Archive the task revision, CLI version, provider model ID, generation settings,
timeouts, pricing date, cache accounting, and execution patch with each study.
API model revisions and nondeterminism can prevent exact replay of old scores.

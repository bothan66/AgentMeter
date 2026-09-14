# CLIProxyAPI integration

AgentMeter uses CLIProxyAPI as an optional compatibility switch between models
and agent harnesses. The proxy is external and is not vendored here.

Copy `config.example.yaml` to an ignored local file, substitute environment
variables or secret-manager values, and start your installed CLIProxyAPI with
that file. Agent containers should address the Docker host gateway rather than
assuming a fixed bridge address. For example, discover it with:

```bash
docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'
```

Then expose the selected base URL as `AGENTMETER_GATEWAY_BASE_URL`. A model must
be explicitly registered with both its upstream name and client-facing alias.
The alias is the model name passed to Codex, Claude Code, or another harness.

Never commit the populated config, API keys, auth stores, proxy logs, or OAuth
files.

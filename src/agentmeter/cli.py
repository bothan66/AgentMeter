"""The installed ``agentmeter`` command and ``python -m agentmeter`` entry point."""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from collections.abc import Sequence

# Heavy optimization dependencies are imported only by their own commands.
COMMANDS = {
    "tables": ("agentmeter.reporting.paper", "Reproduce archived paper tables"),
    "score": ("agentmeter.metrics.cli", "Compute AMS from task-level reward and USD cost"),
    "optimize": (
        "agentmeter.optimization.optimize",
        "Construct trajectory-guided instruction candidates",
    ),
    "summarize": (
        "agentmeter.optimization.summarize",
        "Summarize instruction optimization outputs",
    ),
    "probe": (
        "agentmeter.providers.probe",
        "Send one short Responses request using environment credentials",
    ),
    "proxy-config": (
        "agentmeter.providers.proxy",
        "Render a private provider routing configuration",
    ),
    "manifest": ("agentmeter.tasks", "Build a task manifest with an explicit verifier command"),
}


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch commands without requiring shell scripts or checkout imports."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="agentmeter",
        description="AgentMeter: model–harness evaluation, AMS, and instruction optimization.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    from agentmeter.runtime.cli import register_subcommands

    register_subcommands(subparsers)
    for name, (_, help_text) in COMMANDS.items():
        subparsers.add_parser(name, help=help_text, add_help=False)

    try:
        if arguments and arguments[0] in COMMANDS:
            module = importlib.import_module(COMMANDS[arguments[0]][0])
            return module.main(arguments[1:]) or 0
        args = parser.parse_args(arguments)
        return args.handler(args) or 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        # Avoid logging environment mappings, which may contain API credentials.
        print(f"agentmeter: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("agentmeter: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

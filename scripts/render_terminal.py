"""Render CLI output to SVG for README screenshots (runs the CLI in-process).

python scripts/render_terminal.py docs/img/triage.svg triage incidents/inc-001-db-pool
"""

from __future__ import annotations

import os
import sys

from rich.console import Console

from aiops_assistant import cli

WIDTH = 104


def main() -> None:
    out, args = sys.argv[1], sys.argv[2:]
    with open(os.devnull, "w") as sink:
        console = Console(record=True, width=WIDTH, height=60, force_terminal=True, highlight=False, file=sink)
        cli.console = console
        console.print(f"[bold green]$[/bold green] aiops-assistant {' '.join(args)}")
        try:
            cli.app(args, standalone_mode=False)
        finally:
            console.save_svg(out, title=f"aiops-assistant {args[0]}")


if __name__ == "__main__":
    main()

"""Status command implementation"""

from typing import Optional

import typer

from ..config import RunnerConfig
from ..formatting import console, format_runner_status
from ..process_manager import ProcessManager

status_cmd = typer.Typer(name="status", help="Show runner status", no_args_is_help=True)


@status_cmd.callback(invoke_without_command=True)
def status(
    runner_id: Optional[str] = typer.Option(None, "--runner-id", "-r", help="Runner ID to check"),
    all: bool = typer.Option(False, "--all", "-a", help="Show status of all runners"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
):
    """Show runner status

    Example usage:
        cue-runner status --runner-id <runner_id>
        cue-runner status --all
        cue-runner status --runner-id <runner_id> --verbose
    """
    if all:
        runners = RunnerConfig.get_all_runners()
        if not runners:
            console.print("[yellow]No runners found[/yellow]")
            return

        if json_output:
            all_info = {}
            for rid in runners:
                pm = ProcessManager(rid)
                all_info[rid] = pm.get_runner_info()
            console.print_json(data=all_info)
            return

        for i, rid in enumerate(runners):
            if i > 0:  # Add separator between runners
                console.print("=" * 50)
            pm = ProcessManager(rid)
            info = pm.get_runner_info()
            format_runner_status(rid, info, verbose)
        return

    if runner_id:
        pm = ProcessManager(runner_id)
        info = pm.get_runner_info()

        if json_output:
            console.print_json(data=info)
            return

        format_runner_status(runner_id, info, verbose)
        return

    # If no options specified, show help message
    console.print("[yellow]Please specify one of:[/yellow]")
    console.print("  --runner-id, -r <runner_id>  Show specific runner status")
    console.print("  --all, -a                    Show all runners status")
    console.print("\nAdd --verbose/-v for detailed information")
    console.print("Add --json/-j for JSON output")

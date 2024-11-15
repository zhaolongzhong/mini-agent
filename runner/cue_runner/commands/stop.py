"""Stop command implementation"""

from typing import Optional

import typer
from rich.table import Table

from ..config import RunnerConfig
from ..formatting import console
from ..process_manager import ProcessManager

stop_cmd = typer.Typer(name="stop", help="Stop runner processes", no_args_is_help=True)


def _format_kill_results(runner_id: str, results: dict) -> Table:
    """Format kill results into a table, handling errors gracefully"""
    table = Table(show_header=True)
    table.add_column("Runner ID")
    table.add_column("PID")
    table.add_column("Status")

    if "error" in results:
        table.add_row(runner_id, "N/A", f"[red]{results['error']}")
        return table

    success_count = 0
    for pid, result in results.items():
        if not isinstance(pid, int):  # Skip any non-pid keys
            continue

        # Only show actually killed processes, skip already dead ones
        if "no longer exists" not in str(result):
            status = "[green]Success" if result == "Success" else f"[red]{result}"
            table.add_row(runner_id, str(pid), status)
            if result == "Success":
                success_count += 1

    if success_count == 0:
        table.add_row(runner_id, "N/A", "[yellow]No active processes found")

    return table


@stop_cmd.callback(invoke_without_command=True)
def stop_runner(
    runner_id: Optional[str] = typer.Option(None, "--runner-id", "-r", help="Runner ID to stop"),
    all: bool = typer.Option(False, "--all", "-a", help="Stop all runners"),
    force: bool = typer.Option(False, "--force", "-f", help="Force stop"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
):
    """Stop running runner processes

    Example usage:
        cue-runner stop --all
        cue-runner stop --runner-id <runner_id>
        Add --force to force stop
    """
    if all:
        runners = RunnerConfig.get_all_runners()
        if not runners:
            console.print("[yellow]No runners found[/yellow]")
            return

        success_count = 0
        for rid in runners:
            pm = ProcessManager(rid)
            is_active, status_msg = pm.is_runner_active()

            if is_active:
                if verbose:
                    console.print(f"[blue]Stopping runner '{rid}'...[/blue]")
                results = pm.kill_all(force)
                if any(result == "Success" for result in results.values()):
                    success_count += 1
                console.print(_format_kill_results(rid, results))
            else:
                if verbose:
                    console.print(f"[yellow]Runner '{rid}' is not active: {status_msg}[/yellow]")

        if success_count > 0:
            console.print(f"[green]Successfully stopped {success_count} runner(s)[/green]")
        else:
            console.print("[yellow]No active runners found to stop[/yellow]")
        return

    if runner_id:
        pm = ProcessManager(runner_id)
        is_active, status_msg = pm.is_runner_active()

        if not is_active and not force:
            console.print(f"[yellow]Runner '{runner_id}' is not active: {status_msg}[/yellow]")
            if not typer.confirm("Do you want to clean up any remaining processes?"):
                return

        if not force and not typer.confirm(f"Stop runner '{runner_id}'?"):
            return

        if verbose:
            console.print(f"[blue]Stopping runner '{runner_id}'...[/blue]")

        results = pm.kill_all(force)
        console.print(_format_kill_results(runner_id, results))

        # Verify runner is actually stopped
        is_still_active, _ = pm.is_runner_active()
        if not is_still_active:
            if verbose:
                console.print(f"[green]Runner '{runner_id}' successfully stopped[/green]")
        else:
            console.print(f"[yellow]Warning: Runner '{runner_id}' may still be partially active[/yellow]")
        return

    # If no options specified, show help message
    console.print("[yellow]Please specify one of:[/yellow]")
    console.print("  --runner-id, -r <runner_id>  Stop specific runner")
    console.print("  --all, -a                    Stop all runners")
    console.print("\nAdd --force, -f to force stop")

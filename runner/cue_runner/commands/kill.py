"""Kill command implementation"""

from typing import Optional

import typer
from rich.table import Table

from ..config import RunnerConfig
from ..formatting import console
from ..process_manager import ProcessManager

kill_cmd = typer.Typer(name="kill", help="Kill runner processes", no_args_is_help=True)


@kill_cmd.callback(invoke_without_command=True)
def kill_runner(
    runner_id: Optional[str] = typer.Option(None, "--runner-id", "-r", help="Runner ID to kill"),
    pid: Optional[int] = typer.Option(None, "--pid", "-p", help="Process ID to kill"),
    all: bool = typer.Option(False, "--all", "-a", help="Kill all processes"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill"),
):
    """Kill runner processes

    Example usage:
        cue-runner kill --all
        cue-runner kill --runner-id <runner_id>
        cue-runner kill --pid <pid>
        Add --force to force kill
    """
    if all:
        # Get all runners first
        runners = RunnerConfig.get_all_runners()
        if not runners:
            console.print("[yellow]No runners found[/yellow]")
            return

        all_results = {}
        for rid in runners:
            pm = ProcessManager(rid)
            results = pm.kill_all(force)
            all_results.update({pid: (success, rid) for pid, success in results.items()})

        if not all_results:
            console.print("[yellow]No active processes found[/yellow]")
            return

        table = Table(show_header=True)
        table.add_column("PID")
        table.add_column("Runner")
        table.add_column("Status")

        for pid, (success, rid) in all_results.items():
            table.add_row(str(pid), str(rid), "[green]Success" if success else "[red]Failed")

        console.print(table)
        return

    if runner_id:
        if not force and not typer.confirm(f"Kill all processes for runner '{runner_id}'?"):
            return

        pm = ProcessManager(runner_id)
        results = pm.kill_all(force)

        if not results:
            console.print(f"[yellow]No active processes found for runner '{runner_id}'[/yellow]")
            return

        table = Table(show_header=True)
        table.add_column("PID")
        table.add_column("Status")

        for pid, success in results.items():
            table.add_row(str(pid), "[green]Success" if success else "[red]Failed")

        console.print(table)
        return

    if pid:
        if not force and not typer.confirm(f"Kill process {pid}?"):
            return

        pm = ProcessManager()
        if pm.kill_one(pid, force):
            console.print(f"[green]Successfully killed process {pid}[/green]")
        else:
            console.print(f"[red]Failed to kill process {pid}[/red]")
        return

    # If no options specified, show help message
    console.print("[yellow]Please specify one of:[/yellow]")
    console.print("  --runner-id, -r <runner_id>  Kill specific runner")
    console.print("  --pid, -p <pid>              Kill specific process")
    console.print("  --all, -a                    Kill all runners")
    console.print("\nAdd --force, -f to force kill")

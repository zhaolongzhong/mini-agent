"""List command implementation"""

import typer
from rich.table import Table

from ..config import RunnerConfig
from ..formatting import console, format_runner_status
from ..process_manager import ProcessManager

list_cmd = typer.Typer(name="list", help="List runners and their status")


@list_cmd.callback(invoke_without_command=True)
def list_runners(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
    all_processes: bool = typer.Option(False, "--all", "-a", help="List all Cue processes"),
):
    """List runners and their status"""
    if all_processes:
        pm = ProcessManager()
        processes = pm.find_all_processes()
        if json_output:
            console.print_json(data=processes)
            return

        if not processes:
            console.print("[yellow]No processes found[/yellow]")
            return

        table = Table(show_header=True)
        table.add_column("PID")
        table.add_column("Status")
        table.add_column("Memory (MB)")
        table.add_column("CPU %")
        if verbose:
            table.add_column("Command")
            table.add_column("Runner ID")
            table.add_column("WebSocket")

        for proc in processes:
            row = [
                str(proc["pid"]),
                proc["status"],
                f"{proc['memory_info']['rss'] / 1024 / 1024:.1f}",
                f"{proc['cpu_percent']}%",
            ]
            if verbose:
                row.extend([proc["cmdline"], proc.get("runner_id", "N/A"), proc.get("websocket", "N/A")])
            table.add_row(*row)
        console.print(table)
        return

    runners = RunnerConfig.get_all_runners()
    if not runners:
        console.print("[yellow]No runners found[/yellow]")
        return

    if json_output:
        runner_info = {}
        for runner_id in runners:
            pm = ProcessManager(runner_id)
            runner_info[runner_id] = pm.get_runner_info()
        console.print_json(data=runner_info)
        return

    console.print(f"Found {len(runners)} runners:")
    for runner_id in runners:
        pm = ProcessManager(runner_id)
        info = pm.get_runner_info()
        console.print("=" * 50)
        format_runner_status(runner_id, info, verbose)

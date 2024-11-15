"""Start command implementation"""

import sys
import time
import subprocess
from pathlib import Path

import typer
from rich.table import Table

from ..config import RunnerConfig
from ..formatting import console
from ..process_manager import ProcessManager

start_cmd = typer.Typer(name="start", help="Start runner processes", no_args_is_help=True)


@start_cmd.callback(invoke_without_command=True)
def start_runner(
    runner_id: str = typer.Option("default", "--runner-id", "-r", help="Runner ID to start"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
    force: bool = typer.Option(False, "--force", "-f", help="Force start even if already running"),
):
    """Start a new runner instance

    Example usage:
        cue-runner start
        cue-runner start --runner-id <runner_id>
        cue-runner start --force
    """
    pm = ProcessManager(runner_id)

    # Check if runner is already active
    is_active, status_msg = pm.is_runner_active()
    if is_active and not force:
        console.print(f"[yellow]Runner '{runner_id}' is already running[/yellow]")
        if not typer.confirm("Do you want to restart it?"):
            return

        # Kill existing runner
        if verbose:
            console.print(f"[blue]Stopping existing runner '{runner_id}'...[/blue]")
        kill_results = pm.kill_all(force=True)
        if verbose and kill_results:
            for pid, result in kill_results.items():
                if isinstance(pid, int):
                    console.print(f"[blue]Killed process {pid}: {result}[/blue]")

    # Get runner space info
    runner_space = RunnerConfig.get_runner_space(runner_id)
    _runner_dir = runner_space["space_dir"]
    log_file = runner_space["log_file"]

    try:
        # Find run_cue.py relative to the current module
        package_dir = Path(__file__).resolve().parent.parent.parent
        run_cue_path = package_dir / "run_cue.py"

        if not run_cue_path.exists():
            console.print(f"[red]Could not find run_cue.py at: {run_cue_path}[/red]")
            raise typer.Exit(1)

        # Start the runner process
        cmd = [sys.executable, str(run_cue_path), "--runner-id", runner_id]
        if verbose:
            console.print(f"[blue]Starting command: {' '.join(cmd)}[/blue]")
            console.print(f"[blue]Working directory: {package_dir}[/blue]")

        process = subprocess.Popen(
            cmd,
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(package_dir),  # Set working directory
        )

        # Give the process a moment to start
        time.sleep(1)

        # Verify the process started successfully
        if process.poll() is not None:
            # Read the log file for error details
            try:
                error_details = log_file.read_text().strip()
                console.print("[red]Runner process failed to start:[/red]")
                console.print(f"[red]{error_details}[/red]")
            except Exception:
                console.print(f"[red]Runner process failed to start. Check logs at: {log_file}[/red]")
            raise typer.Exit(1)

        # Wait briefly for the control file to be created
        attempts = 0
        while attempts < 5:
            is_active, status_msg = pm.is_runner_active()
            if is_active:
                break
            if verbose:
                console.print(f"[blue]Waiting for runner to become active (attempt {attempts + 1}/5)...[/blue]")
            time.sleep(1)
            attempts += 1

        # Get runner info for display
        _runner_info = pm.get_runner_info()

        table = Table(show_header=True)
        table.add_column("Property")
        table.add_column("Value")

        table.add_row("Runner ID", runner_id)
        table.add_row("Status", "[green]Started" if is_active else "[yellow]Starting")
        table.add_row("PID", str(process.pid))
        table.add_row("Log File", str(log_file))

        if not is_active:
            console.print("[yellow]Warning: Runner started but not yet fully active[/yellow]")
            console.print(f"[yellow]Status message: {status_msg}[/yellow]")
        else:
            console.print("[green]Runner started successfully[/green]")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Failed to start runner: {str(e)}[/red]")
        raise typer.Exit(1)

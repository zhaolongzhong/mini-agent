"""Clean command implementation"""

from typing import Optional

import typer
from rich.table import Table

from ..config import RunnerConfig
from ..formatting import console
from ..process_manager import ProcessManager

clean_cmd = typer.Typer(name="clean", help="Clean or verify runner files")


@clean_cmd.command(name="files")
def clean_files(
    runner_id: Optional[str] = typer.Option(None, "--runner-id", "-r", help="Clean specific runner"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation and force clean active runners"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
):
    """Clean runner files and directories

    Example usage:
        cue-runner clean files
        cue-runner clean files --runner-id <runner_id>
        cue-runner clean files --force
    """
    if runner_id:
        runners = [runner_id]
    else:
        runners = RunnerConfig.get_all_runners()
        if not runners:
            console.print("[yellow]No runners found[/yellow]")
            return

    if not force:
        msg = "Clean all runner files?" if not runner_id else f"Clean files for runner '{runner_id}'?"
        if not typer.confirm(msg):
            return

    any_active = False
    for rid in runners:
        pm = ProcessManager(rid)
        is_active, status_msg = pm.is_runner_active()

        if is_active and not force:
            console.print(f"[yellow]Warning: Runner '{rid}' is active. Use --force to clean anyway.[/yellow]")
            any_active = True
            continue

        if verbose:
            console.print(f"\n[blue]Cleaning files for runner '{rid}'...[/blue]")

        files_exist = {key: path.exists() for key, path in pm.space.items() if key != "space_dir"}

        cleaned = pm.clean_stale_files()

        table = Table(show_header=True)
        table.add_column("File")
        table.add_column("Status")

        for file_key, success in cleaned.items():
            if file_key == "directory":
                continue

            file_path = pm.space.get(file_key)
            if not file_path:
                continue

            status = "[yellow]Not Found"
            if files_exist.get(file_key):
                if success:
                    status = "[green]Cleaned"
                elif is_active:
                    status = "[yellow]In Use"
                else:
                    status = "[blue]Skipped"

            table.add_row(file_key, status)

        space_dir = pm.space["space_dir"]
        dir_status = "[yellow]Not Found"
        if space_dir.exists():
            if cleaned["directory"]:
                dir_status = "[green]Removed"
            elif any(space_dir.iterdir()):
                dir_status = "[yellow]Not Empty"
            else:
                dir_status = "[blue]Skipped"
        table.add_row("directory", dir_status)

        console.print(f"\nRunner: {rid}")
        console.print(table)

    if any_active:
        console.print("\n[yellow]Note: Some active runners were skipped. Use --force to clean them.[/yellow]")


@clean_cmd.command(name="verify")
def verify_files(
    runner_id: Optional[str] = typer.Option(None, "--runner-id", "-r", help="Verify specific runner"),
):
    """Verify state of runner files and directories

    Example usage:
        cue-runner clean verify
        cue-runner clean verify --runner-id <runner_id>
    """
    if runner_id:
        runners = [runner_id]
    else:
        runners = RunnerConfig.get_all_runners()
        if not runners:
            console.print("[yellow]No runners found[/yellow]")
            return

    for rid in runners:
        pm = ProcessManager(rid)
        is_active, status_msg = pm.is_runner_active()

        table = Table(show_header=True)
        table.add_column("File")
        table.add_column("Status")

        for key, path in pm.space.items():
            if key == "space_dir":
                continue

            if not path.exists():
                status = "[yellow]Not Found"
            elif is_active:
                if key in ["control_file"]:
                    status = "[green]Active"
                else:
                    status = "[blue]Available"
            else:
                status = "[yellow]Stale"

            table.add_row(key, status)

        space_dir = pm.space["space_dir"]
        if not space_dir.exists():
            dir_status = "[yellow]Not Found"
        else:
            if any(space_dir.iterdir()):
                dir_status = "[blue]Contains Files"
            else:
                dir_status = "[yellow]Empty"
        table.add_row("directory", dir_status)

        console.print(f"\nRunner: {rid} ({'[green]Active' if is_active else '[yellow]Inactive'})")
        console.print(table)


@clean_cmd.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Clean or verify runner files.

    Examples:
        Clean files:     cue-runner clean files [options]
        Verify state:    cue-runner clean verify [options]
    """
    if ctx.invoked_subcommand is None:
        console.print("[yellow]Please specify a subcommand:[/yellow]")
        console.print("  files    Clean runner files")
        console.print("  verify   Check runner files state")
        console.print("\nUse --help for more information")

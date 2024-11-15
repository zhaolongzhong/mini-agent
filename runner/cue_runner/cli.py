"""CLI tool for managing Cue runners"""

import typer
from rich.text import Text
from rich.panel import Panel
from rich.console import Console

from .commands import kill_cmd, list_cmd, stop_cmd, clean_cmd, start_cmd, status_cmd

# Initialize main app
app = typer.Typer(
    help="Manage Cue runner processes",
    short_help="Cue runner management tool",
    no_args_is_help=True,
)
console = Console()

app.add_typer(list_cmd)
app.add_typer(status_cmd)
app.add_typer(kill_cmd)
app.add_typer(clean_cmd)
app.add_typer(start_cmd)
app.add_typer(stop_cmd)


def version_callback(value: bool):
    """Print version and exit"""
    if value:
        from .. import __version__

        console.print(f"Cue Runner version: {__version__}")
        raise typer.Exit()


def print_usage():
    """Print detailed usage examples"""
    examples = Panel(
        Text.from_markup("""
[bold]Available Commands:[/bold]

[yellow]list[/yellow]      List all runners and their status
[yellow]status[/yellow]    Show status of a specific runner
[yellow]start[/yellow]     Start runner processes
[yellow]stop[/yellow]      Stop runner processes
[yellow]kill[/yellow]      Kill runner processes
[yellow]clean[/yellow]     Clean runner files

[bold]Common Options:[/bold]

--verbose, -v   Show detailed information
--json, -j      Output in JSON format
--force, -f     Force operations without confirmation
--help          Show command help

[bold]Examples:[/bold]

[yellow]List runners:[/yellow]
  cue-runner list
  cue-runner list --verbose
  cue-runner list --json
  cue-runner list --all

[yellow]Kill processes:[/yellow]
  cue-runner kill --runner-id <runner_id>
  cue-runner kill --pid <pid>
  cue-runner kill --all
  cue-runner kill --force

[yellow]Start a runner:[/yellow]
  cue-runner start
  cue-runner start --runner-id my-runner
  cue-runner start --force  # Restart if already running


[yellow]Stop runners:[/yellow]
  cue-runner stop --runner-id my-runner
  cue-runner stop --all
  cue-runner stop --all --force

[yellow]Clean files:[/yellow]
  cue-runner clean
  cue-runner clean --runner-id <runner_id>
  cue-runner clean --force

[yellow]Check status:[/yellow]
  cue-runner status <runner_id>
  cue-runner status <runner_id> --verbose
  cue-runner status <runner_id> --json
"""),
        title="Cue Runner Help",
        expand=False,
    )
    console.print(examples)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit", callback=version_callback, is_eager=True
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show this help message", is_eager=True),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
):
    """
    Cue Runner - A tool for managing Cue runner processes

    Use --help or -h to see detailed usage information.
    """
    if ctx.invoked_subcommand is None or help:
        print_usage()
        raise typer.Exit()


def cli():
    """Entry point for the CLI"""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    cli()

"""Common formatting utilities for CLI output"""

from rich.table import Table
from rich.console import Console

from .process_manager import ProcessManager

console = Console()


def format_runner_status(runner_id: str, info: dict, verbose: bool = False) -> None:
    """Format and display runner status"""
    pm = ProcessManager(runner_id)
    is_active, reason = pm.is_runner_active()
    info = pm.get_runner_info()

    if verbose:
        console.print_json(data=info)
        return

    table = Table(show_header=True)
    table.add_column("Property")
    table.add_column("Value")

    table.add_row("Runner ID", runner_id)
    table.add_row("Status", "[green]ACTIVE" if is_active else "[red]INACTIVE")
    table.add_row("Directory", info.get("space_dir", "unknown"))

    if "error" in info:
        table.add_row("Error", info["error"])
        console.print(table)
        return

    if not info.get("has_files", False):
        table.add_row("File Status", "No files (inactive)")
        console.print(table)
        return

    control_data = info.get("control_data", {})
    if info.get("is_active", False):
        # table.add_row("Status", control_data.get("status", "unknown"))
        table.add_row("PID", str(control_data.get("pid", "unknown")))
        table.add_row("Last Check", control_data.get("last_check", "unknown"))

        if "process_info" in info and isinstance(info["process_info"], dict):
            proc_info = info["process_info"]
            table.add_row("CPU Usage", f"{proc_info.get('cpu_percent', 'unknown')}%")
            memory = proc_info.get("memory_info", {}).get("rss", 0) / (1024 * 1024)
            table.add_row("Memory Usage", f"{memory:.1f} MB")
    else:
        # table.add_row("Status", "Inactive")
        pass

    if info.get("log_file"):
        table.add_row("Log File", info["log_file"])

    console.print(table)

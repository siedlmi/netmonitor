import typer
from typing import Optional
from rich.console import Console
from netmonitor.monitor import show_top_processes, live_monitor
from netmonitor import core


app = typer.Typer(
    name="NetMonitor",
    help="🔎 A modern CLI tool to monitor network usage and active connections.",
    no_args_is_help=True
)

__version__ = "0.1.2"
console = Console()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        is_eager=True,
        callback=lambda v: (console.print(f"NetMonitor 🚀 v{__version__}") or raise_exit()) if v else None
    )
):
    pass


def raise_exit():
    raise typer.Exit()

@app.command(help="📊 Show top processes by bandwidth or connection count.")
def top(
    delay: float = typer.Option(1.0, "--delay", "-d", help="Sampling delay in seconds (for bandwidth mode).", show_default=True),
    top_n: int = typer.Option(10, "--top", "-t", help="Number of processes to display.", show_default=True),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export format: json or csv."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path for export."),
    sort: Optional[str] = typer.Option("total", "--sort", "-s", help="Sort by field: total, recv, sent, count, etc."),
):
    """One-shot snapshot of top network consumers."""
    if export and export.lower() not in ("json", "csv"):
        typer.echo("❌ Invalid export format. Use 'json' or 'csv'.")
        raise typer.Exit(code=1)

    from netmonitor.monitor import show_top_processes
    show_top_processes(
        delay=delay,
        top_n=top_n,
        export=export.lower() if export else None,
        output=output,
        sort=sort.lower() if sort else "total"
    )

@app.command(help="📡 Live monitor network activity with optional filters.")
def live(
    refresh_interval: float = typer.Option(1.0, "--interval", "-i", help="Refresh interval (sec)", show_default=True),
    top_n: int = typer.Option(15, "--top", "-t", help="Max number of processes", show_default=True),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by connection status"),
    process: Optional[str] = typer.Option(None, "--process", "-p", help="Filter by process name"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export format on exit: json or csv"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename (optional, auto-timestamped if omitted)"),
):
    """Live monitor network usage or active connections by process."""
    from netmonitor.monitor import live_monitor
    live_monitor(refresh_interval, top_n, status, process, export, output)



if __name__ == "__main__":
    app()

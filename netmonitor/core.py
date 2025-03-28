from rich import print
from rich.table import Table

def show_top_processes():
    print("[bold cyan]Top network-consuming processes[/bold cyan]")
    # Placeholder example
    table = Table(title="Network Usage")
    table.add_column("PID", justify="right")
    table.add_column("Process")
    table.add_column("Bytes Sent")
    table.add_column("Bytes Recv")

    table.add_row("1234", "python", "1024 KB", "2048 KB")
    print(table)

def live_monitor():
    print("[green]Live monitoring coming soon...[/green]")

import typer
from netmonitor import core

app = typer.Typer()

@app.command()
def top():
    """Show top processes by network usage"""
    core.show_top_processes()

@app.command()
def live():
    """Live monitor network usage"""
    core.live_monitor()

if __name__ == "__main__":
    app()

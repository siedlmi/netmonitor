import psutil
import time
from netmonitor.utils import supports_per_process_network_io, get_platform
from rich.live import Live
from rich.console import Console
from rich.table import Table
from rich import print
from collections import defaultdict

console = Console()

def _get_net_io_by_pid():
    pid_net = defaultdict(lambda: {"sent": 0, "recv": 0})

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            cons = proc.connections(kind='inet')
            for con in cons:
                if con.status != psutil.CONN_ESTABLISHED:
                    continue
                pid_net[proc.pid]["name"] = proc.info['name']
                pid_net[proc.pid]["sent"] += con.raddr and con.raddr.port or 0  # dummy weight
                pid_net[proc.pid]["recv"] += con.laddr and con.laddr.port or 0  # dummy weight
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue

    return pid_net

def show_top_processes(delay: float = 1.0, top_n: int = 10):
    os_type = get_platform()
    if supports_per_process_network_io():
        _show_top_bandwidth(delay, top_n)
    else:
        _show_top_connections(top_n, os_type)


def _show_top_bandwidth(delay: float, top_n: int):
    print(f"[bold]Collecting network data for {delay} second(s)...[/bold]")
    snapshot1 = _get_net_io_by_pid()
    time.sleep(delay)
    snapshot2 = _get_net_io_by_pid()

    results = []

    for pid in snapshot2:
        if pid not in snapshot1:
            continue
        name = snapshot2[pid].get("name", "unknown")
        sent_delta = snapshot2[pid]["sent"] - snapshot1[pid]["sent"]
        recv_delta = snapshot2[pid]["recv"] - snapshot1[pid]["recv"]
        total = sent_delta + recv_delta
        if total > 0:
            results.append((pid, name, sent_delta, recv_delta, total))

    results.sort(key=lambda x: x[-1], reverse=True)

    table = Table(title="Top Processes by Network Usage")
    table.add_column("PID", justify="right")
    table.add_column("Process")
    table.add_column("Bytes Sent")
    table.add_column("Bytes Recv")
    table.add_column("Total")

    for pid, name, sent, recv, total in results[:top_n]:
        table.add_row(str(pid), name, f"{sent} B", f"{recv} B", f"{total} B")

    print(table)

def _show_top_connections(top_n: int, os_type: str):
    print(f"[bold yellow]Per-process bandwidth is not supported on {os_type.upper()}.[/bold yellow]")
    print("[bold green]Showing processes with the most active network connections instead.[/bold green]")

    conn_counts = {}

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            conns = proc.connections(kind='inet')
            if conns:
                conn_counts[proc.pid] = {
                    "name": proc.info['name'],
                    "count": len(conns)
                }
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue

    sorted_procs = sorted(conn_counts.items(), key=lambda item: item[1]["count"], reverse=True)

    table = Table(title="Top Processes by Active Connections")
    table.add_column("PID", justify="right")
    table.add_column("Process")
    table.add_column("Connections")

    for pid, data in sorted_procs[:top_n]:
        table.add_row(str(pid), data["name"], str(data["count"]))

    print(table)



def live_monitor(refresh_interval: float = 1.0, top_n: int = 15):
    os_type = get_platform()
    if supports_per_process_network_io():
        _live_monitor_full(refresh_interval, top_n)
    else:
        _live_monitor_fallback(refresh_interval, top_n, os_type)

def _live_monitor_full(refresh_interval: float, top_n: int):
    console.clear()
    print("[bold green]Starting full live network monitor (Linux/macOS)... Press Ctrl+C to stop.[/bold green]")

    def build_table(snapshot1, snapshot2):
        ...

    try:
        prev_snapshot = _get_net_io_by_pid()
        with Live(refresh_per_second=1, screen=True) as live:
            while True:
                time.sleep(refresh_interval)
                curr_snapshot = _get_net_io_by_pid()
                table = build_table(prev_snapshot, curr_snapshot)
                live.update(table)
                prev_snapshot = curr_snapshot
    except KeyboardInterrupt:
        print("\n[bold yellow]Exiting live monitor.[/bold yellow]")

    def build_table(snapshot1, snapshot2):
        results = []

        for pid in snapshot2:
            if pid not in snapshot1:
                continue
            name = snapshot2[pid].get("name", "unknown")
            sent_delta = snapshot2[pid]["sent"] - snapshot1[pid]["sent"]
            recv_delta = snapshot2[pid]["recv"] - snapshot1[pid]["recv"]
            total = sent_delta + recv_delta
            if total > 0:
                results.append((pid, name, sent_delta, recv_delta, total))

        results.sort(key=lambda x: x[-1], reverse=True)

        table = Table(title="Live Network Usage", expand=True)
        table.add_column("PID", justify="right")
        table.add_column("Process")
        table.add_column("Bytes Sent/s")
        table.add_column("Bytes Recv/s")
        table.add_column("Total/s")

        for pid, name, sent, recv, total in results[:top_n]:
            table.add_row(str(pid), name, f"{sent}", f"{recv}", f"{total}")

        return table

    try:
        prev_snapshot = _get_net_io_by_pid()
        with Live(refresh_per_second=1, screen=True) as live:
            while True:
                time.sleep(refresh_interval)
                curr_snapshot = _get_net_io_by_pid()
                table = build_table(prev_snapshot, curr_snapshot)
                live.update(table)
                prev_snapshot = curr_snapshot
    except KeyboardInterrupt:
        print("\n[bold yellow]Exiting live monitor.[/bold yellow]")

def _live_monitor_fallback(refresh_interval: float, top_n: int, os_type: str):
    print(f"[bold yellow]Per-process bandwidth is not supported on {os_type.upper()}.[/bold yellow]")
    print("[bold green]Showing active network connections instead. Press Ctrl+C to stop.[/bold green]")

    def get_connections():
        conns = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections(kind='inet'):
                    conns.append({
                        "pid": proc.pid,
                        "name": proc.info['name'],
                        "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                        "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                        "status": conn.status,
                    })
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        return conns

    def build_conn_table():
        conns = get_connections()
        table = Table(title="Active Network Connections", expand=True)
        table.add_column("PID", justify="right")
        table.add_column("Process")
        table.add_column("Local Address")
        table.add_column("Remote Address")
        table.add_column("Status")

        for conn in conns[:top_n]:
            table.add_row(
                str(conn["pid"]),
                conn["name"],
                conn["laddr"],
                conn["raddr"],
                conn["status"]
            )
        return table

    try:
        with Live(refresh_per_second=1, screen=True) as live:
            while True:
                table = build_conn_table()
                live.update(table)
                time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print("\n[bold yellow]Exiting fallback monitor.[/bold yellow]")


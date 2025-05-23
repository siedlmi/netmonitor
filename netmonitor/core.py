import psutil
import time
import socket
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
    print("[bold green]Showing enriched process connection info instead.[/bold green]")

    connection_data = {}

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            conns = proc.connections(kind='inet')
            if not conns:
                continue

            protocols = {"TCP": 0, "UDP": 0}
            remotes = set()

            for c in conns:
                proto = "TCP" if c.type == socket.SOCK_STREAM else "UDP"
                protocols[proto] += 1
                if c.raddr:
                    remotes.add(c.raddr.ip)

            connection_data[proc.pid] = {
                "name": proc.info['name'],
                "count": len(conns),
                "tcp": protocols["TCP"],
                "udp": protocols["UDP"],
                "remotes": len(remotes)
            }

        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue

    sorted_procs = sorted(connection_data.items(), key=lambda item: item[1]["count"], reverse=True)

    table = Table(title="Top Processes by Active Connections")
    table.add_column("PID", justify="right")
    table.add_column("Process")
    table.add_column("Conns")
    table.add_column("TCP", justify="right")
    table.add_column("UDP", justify="right")
    table.add_column("Remote Hosts", justify="right")

    for pid, data in sorted_procs[:top_n]:
        table.add_row(
            str(pid),
            data["name"],
            str(data["count"]),
            str(data["tcp"]),
            str(data["udp"]),
            str(data["remotes"])
        )

    print(table)



def live_monitor(refresh_interval: float = 1.0, top_n: int = 10, status: str = None, process: str = None):
    os_type = get_platform()
    if supports_per_process_network_io():
        _live_monitor_full(refresh_interval, top_n)
    else:
        _live_monitor_fallback(refresh_interval, top_n, os_type, status, process)


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

from collections import Counter
import socket

def _live_monitor_fallback(refresh_interval: float, top_n: int, os_type: str, status: str = None, process_filter: str = None):
    print(f"[bold yellow]Per-process bandwidth is not supported on {os_type.upper()}.[/bold yellow]")
    print("[bold green]Showing real-time connection activity instead. Press Ctrl+C to stop.[/bold green]")

    def get_process_connection_summary():
        summary = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if process_filter and process_filter.lower() not in proc.info['name'].lower():
                    continue

                conns = proc.connections(kind='inet')
                if not conns:
                    continue

                if status:
                    conns = [c for c in conns if c.status.lower() == status.lower()]
                    if not conns:
                        continue

                tcp_count = sum(1 for c in conns if c.type == socket.SOCK_STREAM)
                udp_count = sum(1 for c in conns if c.type == socket.SOCK_DGRAM)
                remotes = [c.raddr.ip for c in conns if c.raddr]
                remote_counts = Counter(remotes)
                most_common_remote = remote_counts.most_common(1)[0][0] if remote_counts else "-"

                status_counts = Counter(c.status for c in conns)
                status_summary = " ".join(f"{s[0]}:{count}" for s, count in status_counts.items())

                summary.append({
                    "pid": proc.pid,
                    "name": proc.info['name'],
                    "total": len(conns),
                    "tcp": tcp_count,
                    "udp": udp_count,
                    "remote_hosts": len(set(remotes)),
                    "top_remote": most_common_remote,
                    "status_summary": status_summary,
                })

            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue

        return sorted(summary, key=lambda x: x["total"], reverse=True)


    def build_table():
        data = get_process_connection_summary()
        table = Table(title="Active Network Connections (Live)", expand=True)
        table.add_column("PID", justify="right")
        table.add_column("Process")
        table.add_column("Conns", justify="right")
        table.add_column("TCP", justify="right")
        table.add_column("UDP", justify="right")
        table.add_column("Remote Hosts", justify="right")
        table.add_column("Top Remote IP")
        table.add_column("Status Summary")

        for proc in data[:top_n]:
            table.add_row(
                str(proc["pid"]),
                proc["name"],
                str(proc["total"]),
                str(proc["tcp"]),
                str(proc["udp"]),
                str(proc["remote_hosts"]),
                proc["top_remote"],
                proc["status_summary"]
            )

        table.add_row(
            "", "[bold]Total[/bold]",
            str(sum(proc["total"] for proc in data[:top_n])),
            "", "", "",
            f"{len(data[:top_n])} processes", ""
        )

        table.caption = (
            "[dim]Legend: E=ESTABLISHED, T=TIME_WAIT, C=CLOSE_WAIT, S=SYN_SENT, F=FIN_WAIT\n"
            "Filters: Use --status ESTABLISHED or --process chrome"
        )

        return table

    try:
        with Live(refresh_per_second=1, screen=True) as live:
            while True:
                table = build_table()
                live.update(table)
                time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print("\n[bold yellow]Exiting fallback monitor.[/bold yellow]")



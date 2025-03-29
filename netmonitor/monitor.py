import psutil
import time
import socket
import json
import csv
from collections import defaultdict, Counter
from datetime import datetime
from rich.live import Live
from rich.console import Console
from rich.table import Table
from rich import print
from netmonitor.utils import (
    supports_per_process_network_io,
    get_platform,
    filter_process_name,
    filter_connection_status,
    format_bytes
)

console = Console()

def show_top_processes(delay: float = 1.0, top_n: int = 10, export: str = None, output: str = None, sort: str = "total"):
    os_type = get_platform()
    if supports_per_process_network_io():
        _show_top_bandwidth(delay, top_n, export, output, sort)
    else:
        _show_top_connections(top_n, os_type, export, output, sort)

def _get_net_io_by_pid():
    pid_net = defaultdict(lambda: {"sent": 0, "recv": 0})
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            cons = proc.connections(kind='inet')
            for con in cons:
                if con.status != psutil.CONN_ESTABLISHED:
                    continue
                pid_net[proc.pid]["name"] = proc.info['name']
                pid_net[proc.pid]["sent"] += con.raddr.port if con.raddr else 0  # placeholder
                pid_net[proc.pid]["recv"] += con.laddr.port if con.laddr else 0  # placeholder
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return pid_net

def _show_top_bandwidth(delay: float, top_n: int, export: str = None, output: str = None, sort: str = "total"):
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
            results.append({
                "pid": pid,
                "name": name,
                "sent": sent_delta,
                "recv": recv_delta,
                "total": total
            })

    results.sort(key=lambda x: x.get(sort, x["total"]), reverse=True)

    if export == "json":
        content = json.dumps(results[:top_n], indent=2)
        if output:
            with open(output, "w") as f:
                f.write(content)
        else:
            print(content)
        return
    elif export == "csv":
        if output:
            with open(output, "w", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["pid", "name", "sent", "recv", "total"])
                writer.writeheader()
                writer.writerows(results[:top_n])
        else:
            writer = csv.DictWriter(console.file, fieldnames=["pid", "name", "sent", "recv", "total"])
            writer.writeheader()
            writer.writerows(results[:top_n])
        return

    table = Table(title="Top Processes by Network Usage")
    table.add_column("PID", justify="right")
    table.add_column("Process")
    table.add_column("Bytes Sent")
    table.add_column("Bytes Recv")
    table.add_column("Total")

    for row in results[:top_n]:
        table.add_row(
            str(row["pid"]),
            row["name"],
            format_bytes(row["sent"]),
            format_bytes(row["recv"]),
            format_bytes(row["total"])
        )

    print(table)

def _show_top_connections(top_n: int, os_type: str, export: str = None, output: str = None, sort: str = "count"):
    print(f"[bold yellow]Per-process bandwidth is not supported on {os_type.upper()}.[/bold yellow]")
    print("[bold green]Showing enriched process connection info instead.[/bold green]")
    connection_data = []

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
            connection_data.append({
                "pid": proc.pid,
                "name": proc.info['name'],
                "count": len(conns),
                "tcp": protocols["TCP"],
                "udp": protocols["UDP"],
                "remotes": len(remotes)
            })
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue

    sorted_data = sorted(connection_data, key=lambda item: item.get(sort, item["count"]), reverse=True)

    if export == "json":
        content = json.dumps(sorted_data[:top_n], indent=2)
        if output:
            with open(output, "w") as f:
                f.write(content)
        else:
            print(content)
        return
    elif export == "csv":
        if output:
            with open(output, "w", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["pid", "name", "count", "tcp", "udp", "remotes"])
                writer.writeheader()
                writer.writerows(sorted_data[:top_n])
        else:
            writer = csv.DictWriter(console.file, fieldnames=["pid", "name", "count", "tcp", "udp", "remotes"])
            writer.writeheader()
            writer.writerows(sorted_data[:top_n])
        return

    table = Table(title="Top Processes by Active Connections")
    table.add_column("PID", justify="right")
    table.add_column("Process")
    table.add_column("Conns")
    table.add_column("TCP", justify="right")
    table.add_column("UDP", justify="right")
    table.add_column("Remote Hosts", justify="right")

    for row in sorted_data[:top_n]:
        table.add_row(
            str(row["pid"]), row["name"], str(row["count"]), str(row["tcp"]), str(row["udp"]), str(row["remotes"])
        )

    print(table)

# live_monitor functions remain unchanged

def live_monitor(refresh_interval: float = 1.0, top_n: int = 10, status: str = None, process: str = None, export: str = None, output: str = None):
    os_type = get_platform()
    if supports_per_process_network_io():
        _live_monitor_full(refresh_interval, top_n, export, output)
    else:
        _live_monitor_fallback(refresh_interval, top_n, os_type, status, process, export, output)

def _live_monitor_fallback(refresh_interval: float, top_n: int, os_type: str, status: str = None, process_filter: str = None, export: str = None, output: str = None):
    print(f"[bold yellow]Per-process bandwidth is not supported on {os_type.upper()}.[/bold yellow]")
    print("[bold green]Showing real-time connection activity instead. Press Ctrl+C to stop.[/bold green]")

    def get_process_connection_summary():
        summary = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if process_filter and not filter_process_name(proc.info['name'], process_filter):
                    continue
                conns = proc.connections(kind='inet')
                if not conns:
                    continue
                if status:
                    conns = [c for c in conns if filter_connection_status(c.status, status)]
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

    def build_table(data):
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
                str(proc["pid"]), proc["name"], str(proc["total"]), str(proc["tcp"]),
                str(proc["udp"]), str(proc["remote_hosts"]), proc["top_remote"], proc["status_summary"]
            )

        table.add_row(
            "", "[bold]Total[/bold]", str(sum(proc["total"] for proc in data[:top_n])),
            "", "", "", f"{len(data[:top_n])} processes", ""
        )

        table.caption = (
            "[dim]Legend: E=ESTABLISHED, T=TIME_WAIT, C=CLOSE_WAIT, S=SYN_SENT, F=FIN_WAIT\n"
            "Filters: Use --status ESTABLISHED or --process chrome"
        )
        return table

    try:
        with Live(refresh_per_second=1, screen=True) as live:
            while True:
                data = get_process_connection_summary()
                table = build_table(data)
                live.update(table)
                time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print("\n[bold yellow]Exiting fallback monitor.[/bold yellow]")
        if export in ("json", "csv"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = output or f"netmonitor_snapshot_{timestamp}.{export}"
            snapshot = get_process_connection_summary()[:top_n]
            if export == "json":
                with open(filename, "w") as f:
                    json.dump(snapshot, f, indent=2)
            elif export == "csv":
                with open(filename, "w", newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        "pid", "name", "total", "tcp", "udp", "remote_hosts", "top_remote", "status_summary"])
                    writer.writeheader()
                    writer.writerows(snapshot)
            print(f"[green]Snapshot exported to:[/green] {filename}")

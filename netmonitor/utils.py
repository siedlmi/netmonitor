import platform


def get_platform() -> str:
    """Return a simplified name for the current platform."""
    system = platform.system().lower()
    if "linux" in system:
        return "linux"
    elif "darwin" in system:
        return "macos"
    elif "windows" in system:
        return "windows"
    return "unknown"


def supports_per_process_network_io() -> bool:
    """Return True if per-process network usage is supported."""
    return get_platform() in ("linux", "macos")


def format_bytes(size: int) -> str:
    """Format bytes as human-readable units (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def filter_process_name(name: str, filter_str: str) -> bool:
    """Check if process name matches (case-insensitive substring)."""
    return filter_str.lower() in name.lower()


def filter_connection_status(status: str, target: str) -> bool:
    """Check if connection status matches (case-insensitive)."""
    return status.lower() == target.lower()

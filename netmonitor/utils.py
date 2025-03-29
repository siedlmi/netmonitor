import platform

def get_platform():
    """Return a simplified OS name."""
    system = platform.system().lower()
    if "linux" in system:
        return "linux"
    elif "darwin" in system:
        return "macos"
    elif "windows" in system:
        return "windows"
    else:
        return "unknown"

def supports_per_process_network_io():
    """Return True if we can (accurately) track per-process network usage."""
    os = get_platform()
    return os in ("linux", "macos")  # not supported on Windows (yet)

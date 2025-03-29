# NetMonitor

**NetMonitor** is a modern, cross-platform CLI tool for real-time and snapshot-based network monitoring. Built with Python, `psutil`, and `Rich`, it offers insightful visualizations and export capabilities to track bandwidth and connection usage per process.

![screenshot](docs/demo.gif)

---

## 🔧 Features

- 🧠 Intelligent OS detection (Linux/macOS/Windows)
- 📶 Live per-process bandwidth monitoring (Linux/macOS)
- 📡 Real-time connection viewer for Windows with ETW fallback
- 🧩 Filtering by status, process name, and protocol (tcp/udp)
- 📊 Export snapshot to JSON or CSV
- 💡 CLI-first with modern UX using [Rich](https://github.com/Textualize/rich)

---

## 🚀 Installation

### From source
```bash
git clone https://github.com/siedlmi/netmonitor.git
cd netmonitor
pip install .
```

### As a global CLI
```bash
pip install --editable .
```

---

## 🧪 Example Usage

### Show top processes (snapshot mode)
```bash
netmonitor top
netmonitor top --export csv --output traffic.csv
netmonitor top --sort recv
```

### Live view with filters
```bash
netmonitor live --protocol tcp --process chrome --status ESTABLISHED
netmonitor live --export json
```

### Windows-specific ETW monitor (requires admin)
```bash
netmonitor winbandwidth --duration 15
```

---

## 🛠️ CLI Options

```bash
netmonitor --help
netmonitor top --help
netmonitor live --help
```

---

## 📦 Requirements
- Python 3.8+
- [psutil](https://pypi.org/project/psutil/)
- [rich](https://pypi.org/project/rich/)
- [typer](https://pypi.org/project/typer/)

---

## 🧩 Architecture
- `monitor.py`: main monitoring logic
- `cli.py`: Typer-powered CLI
- `etw_monitor.py`: Windows-only bandwidth tracing using ETW
- `utils.py`: cross-platform helpers

---

## 📘 License
MIT © YourName

---
# Per-Process Bandwidth Tracker using eBPF

A real-time network usage tracker using eBPF to measure send/receive bandwidth per process with support for per-remote IP tracking, protocol filtering, and historical usage storage.

## Features

- **Real-time monitoring**: Track network bandwidth usage per process in real-time
- **Per-IP tracking**: Monitor traffic to/from specific remote IP addresses
- **Protocol filtering**: Separate TCP and UDP traffic statistics
- **Historical storage**: Store usage data in SQLite for reporting
- **Web UI**: Simple web interface for visualization
- **CLI interface**: Command-line tool for quick stats

## Architecture

```
┌─────────────────────────────────────────┐
│         Kernel Space (eBPF)             │
├─────────────────────────────────────────┤
│  • tcp_sendmsg hook (TX tracking)       │
│  • tcp_recvmsg hook (RX tracking)       │
│  • udp_sendmsg hook (UDP TX)            │
│  • udp_recvmsg hook (UDP RX)            │
│  • Per-process/IP aggregation in maps   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      User Space (Python/BCC)            │
├─────────────────────────────────────────┤
│  • Read eBPF maps periodically          │
│  • Process aggregation                  │
│  • Store in SQLite                      │
│  • Expose via Flask API                 │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Visualization Layer             │
├─────────────────────────────────────────┤
│  • Web UI (HTML/CSS/JS)                 │
│  • CLI tool                             │
│  • Historical reports                   │
└─────────────────────────────────────────┘
```

## Requirements

### System Requirements
- Linux kernel 4.15+ (with eBPF support)
- Root/sudo access

### Software Dependencies
```bash
# Install BCC (eBPF toolkit)
sudo apt-get update
sudo apt-get install -y bpfcc-tools linux-headers-$(uname -r)
sudo apt-get install -y python3-bpfcc

# Python packages
pip3 install -r requirements.txt
```

## Project Structure

```
.
├── ebpf_tracker.py          # Main eBPF program (BCC)
├── storage.py               # SQLite storage layer
├── web_server.py            # Flask web server
├── cli.py                   # Command-line interface
├── requirements.txt         # Python dependencies
├── static/
│   ├── index.html          # Web UI
│   ├── style.css           # Styling
│   └── app.js              # Frontend JS
└── README.md               # This file
```

## Installation

1. Clone the repository
2. Install system dependencies (see above)
3. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

## Usage

### Start the Tracker

```bash
make run # command line version
make run-web # web version
```

## How It Works

1. **eBPF Hooks**: The program attaches eBPF probes to kernel functions:
   - `tcp_sendmsg`: Captures TCP send operations
   - `tcp_recvmsg`: Captures TCP receive operations
   - `udp_sendmsg`: Captures UDP send operations
   - `udp_recvmsg`: Captures UDP receive operations

2. **Data Collection**: For each network operation, the eBPF program records:
   - Process ID (PID)
   - Process name
   - Remote IP address
   - Protocol (TCP/UDP)
   - Bytes sent/received
   - Timestamp

3. **Aggregation**: Data is aggregated in eBPF maps and periodically read by the user-space program

4. **Storage**: Historical data is stored in SQLite for long-term analysis

5. **Visualization**: Real-time and historical data can be viewed via web UI or CLI

## Performance

- **Minimal overhead**: eBPF runs in kernel space with minimal performance impact
- **Efficient aggregation**: Data is aggregated in kernel space before moving to user space
- **Scalable**: Can handle high-traffic systems

## Security Considerations

- Requires root privileges to load eBPF programs
- Only tracks local processes (not forwarded traffic)
- Data is stored locally in SQLite

## License

MIT License

## References

- [BCC Documentation](https://github.com/iovisor/bcc)
- [eBPF Documentation](https://ebpf.io/)
- [Linux Kernel Networking](https://www.kernel.org/doc/html/latest/networking/)

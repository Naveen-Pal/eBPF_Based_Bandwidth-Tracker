# eBPF Bandwidth Tracker - Development Guide

## Project Overview

This project uses eBPF (Extended Berkeley Packet Filter) to track network bandwidth usage per process in real-time. It consists of:

1. **Kernel Space (eBPF)**: C code that runs in the kernel
2. **User Space (Python)**: Data collection, storage, and visualization
3. **Web Interface**: Real-time dashboard for monitoring
4. **CLI Tool**: Command-line interface for queries

## Architecture Deep Dive

### 1. eBPF Kernel Hooks

The tracker attaches to four kernel functions:

```c
- tcp_sendmsg()   // Captures TCP send operations
- tcp_recvmsg()   // Captures TCP receive operations  
- udp_sendmsg()   // Captures UDP send operations
- udp_recvmsg()   // Captures UDP receive operations
```

Each hook:
1. Extracts process information (PID, name)
2. Gets remote IP from socket structure
3. Records bytes transferred
4. Updates aggregation maps

### 2. Data Flow

```
Kernel Space:
  Network syscall → eBPF hook → Extract metadata → Update BPF map
                                                         ↓
User Space:
  Poll BPF maps → Aggregate data → Store in SQLite → Serve via API
                                                         ↓
Visualization:
  Web UI / CLI ← REST API ← Flask ← SQLite ← Data collector
```

### 3. Key Data Structures

#### eBPF Map Key
```c
struct bandwidth_key_t {
    u32 pid;           // Process ID
    u32 remote_ip;     // Remote IP address
    u16 protocol;      // 0=TCP, 1=UDP
    u16 direction;     // 0=TX, 1=RX
}
```

#### eBPF Map Value
```c
struct bandwidth_data_t {
    u64 bytes;         // Total bytes
    u64 packets;       // Packet count
    u64 timestamp;     // Last update
    char comm[16];     // Process name
}
```

## Development Setup

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get install -y \
    build-essential \
    linux-headers-$(uname -r) \
    bpfcc-tools \
    python3-bpfcc \
    python3-pip \
    clang \
    llvm

# Python development dependencies
pip3 install \
    bcc \
    flask \
    flask-cors \
    psutil \
    tabulate
```

### Running in Development Mode

```bash
# Terminal 1: Start tracker with web server
sudo python3 ebpf_tracker.py --web --interval 1

# Terminal 2: Monitor logs
tail -f /var/log/syslog | grep -i bpf

# Terminal 3: Test CLI
sudo python3 cli.py --live
```

## Code Organization

```
project/
├── ebpf_tracker.py      # Main eBPF program (BCC)
│   ├── BPF_PROGRAM      # eBPF C code (kernel space)
│   └── BandwidthTracker # Python class (user space)
│
├── storage.py           # Database layer
│   └── BandwidthStorage # SQLite operations
│
├── web_server.py        # Flask API server
│   └── REST endpoints   # /api/current, /api/history, etc.
│
├── cli.py              # Command-line interface
│   └── CLI commands    # Display, filter, report
│
└── static/             # Web UI
    ├── index.html      # Main page
    ├── style.css       # Styling
    └── app.js          # Frontend logic
```

## Extending the Project

### Adding New Protocols

To track additional protocols (e.g., ICMP):

1. Add eBPF hook:
```c
int trace_icmp_sendmsg(struct pt_regs *ctx, ...) {
    // Extract ICMP data
    key.protocol = 2; // ICMP
    // ... update map
}
```

2. Attach hook in Python:
```python
self.bpf.attach_kprobe(event="icmp_sendmsg", fn_name="trace_icmp_sendmsg")
```

### Adding Custom Metrics

To track additional metrics (e.g., connection count):

1. Modify eBPF structure:
```c
struct bandwidth_data_t {
    u64 bytes;
    u64 packets;
    u64 connections;  // New field
    // ...
}
```

2. Update aggregation logic in `ebpf_tracker.py`

### Adding New API Endpoints

In `web_server.py`:

```python
@app.route('/api/custom/endpoint')
def custom_endpoint():
    # Your logic here
    return jsonify(results)
```

### Database Schema Changes

To add new tables:

```python
# In storage.py
def _create_tables(self):
    self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS new_table (
            id INTEGER PRIMARY KEY,
            // ... columns
        )
    """)
```

## Performance Optimization

### 1. eBPF Level

- **Use BPF_HASH with appropriate size**
  ```python
  BPF_HASH(bandwidth_map, struct bandwidth_key_t, struct bandwidth_data_t, 10240);
  ```

- **Minimize map lookups**
  - Cache frequently accessed data
  - Use per-CPU maps for better performance

### 2. User Space

- **Batch database writes**
  ```python
  # Instead of individual inserts
  cursor.executemany("INSERT ...", batch_data)
  ```

- **Use connection pooling**
- **Implement data retention policies**

### 3. Web UI

- **Implement pagination** for large datasets
- **Use WebSockets** for real-time updates
- **Add caching** for frequently accessed data

## Testing

### Unit Tests

Create `tests/test_storage.py`:

```python
import unittest
from storage import BandwidthStorage

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.storage = BandwidthStorage(":memory:")
    
    def test_insert_record(self):
        self.storage.insert_bandwidth_record(
            timestamp=datetime.now(),
            pid=1234,
            process_name="test",
            tx_bytes=1024,
            rx_bytes=2048,
            protocol="TCP"
        )
        
        stats = self.storage.get_summary_stats(hours=1)
        self.assertEqual(stats['total_tx'], 1024)
```

Run tests:
```bash
python3 -m pytest tests/
```

### Integration Tests

Test end-to-end flow:

```bash
# Start tracker
sudo python3 ebpf_tracker.py --web &

# Generate traffic
curl https://www.google.com

# Check API
curl http://localhost:8080/api/current | jq

# Verify database
sqlite3 bandwidth.db "SELECT COUNT(*) FROM bandwidth_records;"
```

## Debugging

### eBPF Debugging

1. **Check BPF program compilation**:
   ```python
   # In ebpf_tracker.py, add:
   print(BPF_PROGRAM)  # View generated C code
   ```

2. **Use BPF debugging**:
   ```python
   bpf = BPF(text=BPF_PROGRAM, debug=0x4)  # Enable debug output
   ```

3. **Check kernel logs**:
   ```bash
   sudo dmesg | tail -100
   ```

### Python Debugging

Add logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Processing {len(stats)} entries")
```

### Web UI Debugging

Use browser developer tools:
- Console: Check for JavaScript errors
- Network: Verify API calls
- Storage: Inspect local data

## Security Considerations

### 1. Privilege Management

- Run with minimum required privileges
- Consider using capabilities instead of root:
  ```bash
  sudo setcap cap_sys_admin,cap_bpf+ep /usr/bin/python3
  ```

### 2. Data Privacy

- Implement access controls for sensitive data
- Consider encrypting stored data
- Add authentication to web UI

### 3. Input Validation

- Sanitize all user inputs
- Validate API parameters
- Prevent SQL injection

## Production Deployment

### 1. Systemd Service

Already provided in `install.sh`. Configure:

```bash
sudo systemctl enable ebpf-bandwidth-tracker
sudo systemctl start ebpf-bandwidth-tracker
```

### 2. Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name bandwidth-tracker.example.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Log Rotation

Create `/etc/logrotate.d/ebpf-tracker`:

```
/var/log/ebpf-tracker/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
}
```

### 4. Monitoring

Add Prometheus metrics:

```python
from prometheus_client import Counter, Gauge

bandwidth_counter = Counter('bandwidth_bytes_total', 'Total bandwidth', ['direction', 'protocol'])
active_processes = Gauge('active_processes', 'Number of active processes')
```

## Future Enhancements

1. **Container Support**: Track bandwidth per container
2. **Kubernetes Integration**: Monitor pod-level bandwidth
3. **Alerts**: Threshold-based notifications
4. **Machine Learning**: Anomaly detection
5. **Distributed Tracing**: Correlate with application traces
6. **Export Formats**: Prometheus, Grafana, ELK stack

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Resources

- [BCC Documentation](https://github.com/iovisor/bcc/blob/master/docs/reference_guide.md)
- [eBPF Tutorial](https://ebpf.io/what-is-ebpf)
- [Kernel Network Stack](https://www.kernel.org/doc/html/latest/networking/)
- [BPF Performance Tools Book](http://www.brendangregg.com/bpf-performance-tools-book.html)

## License

MIT License - See LICENSE file for details

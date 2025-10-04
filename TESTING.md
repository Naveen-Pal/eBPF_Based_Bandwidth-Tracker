# eBPF Bandwidth Tracker - Testing Guide

This guide helps you test the bandwidth tracker functionality.

## Prerequisites

Ensure the tracker is installed and running:
```bash
sudo python3 ebpf_tracker.py --web
```

## Test Scenarios

### 1. Generate Network Traffic

#### Test with wget/curl
```bash
# Download a large file
wget https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso

# Or use curl
curl -O https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso
```

#### Test with iperf3
```bash
# Install iperf3
sudo apt-get install iperf3

# Terminal 1: Start iperf3 server
iperf3 -s

# Terminal 2: Run client test
iperf3 -c localhost -t 30
```

#### Test with ping
```bash
# Generate ICMP traffic
ping -c 100 8.8.8.8
```

#### Test with DNS queries
```bash
# Install dnsutils
sudo apt-get install dnsutils

# Generate DNS traffic
for i in {1..100}; do nslookup google.com; done
```

### 2. Web Browsing Test

Open a web browser and visit various websites:
```bash
# Launch browsers
firefox &
google-chrome &

# Visit sites that generate traffic
# - YouTube videos
# - Large image galleries
# - Download files
```

### 3. Network Service Test

#### HTTP Server
```bash
# Python HTTP server
python3 -m http.server 8000 &

# Generate requests
for i in {1..50}; do curl http://localhost:8000/ > /dev/null; done
```

#### SSH Transfer
```bash
# Transfer files over SSH
scp largefile.iso user@remote-server:/tmp/
```

### 4. Verify Tracking

#### Check Real-time Stats (CLI)
```bash
# Monitor live bandwidth
sudo python3 cli.py --live --interval 1

# Check top processes
sudo python3 cli.py --top 20 --hours 1

# Protocol breakdown
sudo python3 cli.py --protocol-breakdown

# IP breakdown for specific process
sudo python3 cli.py --ip-breakdown --process firefox
```

#### Check Web UI
1. Open browser to http://localhost:8080
2. Navigate through tabs:
   - **Real-time**: See current bandwidth usage
   - **History**: View historical data
   - **Protocols**: See TCP/UDP breakdown
   - **Remote IPs**: See which IPs are being contacted
   - **Charts**: View bandwidth over time

### 5. Database Verification

```bash
# Check SQLite database
sqlite3 data/bandwidth.db

# Run queries
sqlite> SELECT process_name, SUM(tx_bytes + rx_bytes) as total 
        FROM bandwidth_records 
        GROUP BY process_name 
        ORDER BY total DESC 
        LIMIT 10;

sqlite> SELECT COUNT(*) FROM bandwidth_records;

sqlite> .quit
```

## Expected Results

### What You Should See:

1. **Process List**: Active network processes (browsers, wget, curl, etc.)
2. **TX/RX Data**: Separate upload and download statistics
3. **Protocol Split**: TCP vs UDP traffic breakdown
4. **Remote IPs**: List of destination IPs being contacted
5. **Charts**: Time-series visualization of bandwidth

### Typical Bandwidth Values:

- **wget/curl downloading**: High RX (download), low TX
- **iperf3**: Balanced TX/RX or high in one direction
- **Web browsing**: Moderate RX, low TX
- **Video streaming**: High RX
- **SSH/SCP**: Varies based on operation

## Performance Testing

### Test eBPF Overhead

```bash
# Baseline test without tracker
time curl -O https://example.com/largefile

# Test with tracker running
sudo python3 ebpf_tracker.py &
time curl -O https://example.com/largefile
```

The overhead should be minimal (< 1% typically).

## Troubleshooting Tests

### Check eBPF Program is Loaded

```bash
# List loaded BPF programs
sudo bpftool prog list

# Check BPF maps
sudo bpftool map list
```

### Verify Kernel Support

```bash
# Check kernel version
uname -r

# Check kernel config
grep CONFIG_BPF /boot/config-$(uname -r)

# Should show:
# CONFIG_BPF=y
# CONFIG_BPF_SYSCALL=y
```

### Test Database Connection

```bash
# Python test
python3 -c "from storage import BandwidthStorage; s = BandwidthStorage('test.db'); print('OK')"
```

### Check for Errors

```bash
# Check system logs
sudo journalctl -u ebpf-bandwidth-tracker -f

# Check for BCC errors
sudo dmesg | grep -i bpf
```

## Automated Test Script

Create `test.sh`:

```bash
#!/bin/bash

echo "=== Testing eBPF Bandwidth Tracker ==="

# 1. Start tracker in background
echo "Starting tracker..."
sudo python3 ebpf_tracker.py --web &
TRACKER_PID=$!
sleep 5

# 2. Generate test traffic
echo "Generating test traffic..."
curl -s https://www.google.com > /dev/null
ping -c 10 8.8.8.8 > /dev/null

# 3. Wait for data collection
echo "Waiting for data collection..."
sleep 10

# 4. Check CLI output
echo "Checking CLI output..."
sudo python3 cli.py --top 5

# 5. Test API
echo "Testing API..."
curl -s http://localhost:8080/api/current | python3 -m json.tool

# 6. Cleanup
echo "Cleaning up..."
sudo kill $TRACKER_PID

echo "=== Test Complete ==="
```

Run it:
```bash
chmod +x test.sh
./test.sh
```

## Performance Benchmarks

Expected performance metrics:
- **CPU Overhead**: < 1%
- **Memory Usage**: ~50-100 MB
- **Disk I/O**: Minimal (SQLite writes)
- **Network Impact**: Negligible (monitoring only)

## Validation Checklist

- [ ] eBPF program loads without errors
- [ ] Processes appear in real-time view
- [ ] TX/RX bytes increase with traffic
- [ ] Protocol breakdown shows TCP/UDP
- [ ] Remote IPs are tracked correctly
- [ ] Historical data is stored in database
- [ ] Web UI loads and displays data
- [ ] Charts render properly
- [ ] CLI commands work correctly
- [ ] No kernel errors in dmesg

## Common Issues and Solutions

### No Data Appearing
- Ensure running with sudo/root
- Check if BCC is properly installed
- Verify kernel supports eBPF

### High CPU Usage
- Reduce polling interval
- Check for database issues
- Verify eBPF program efficiency

### Database Errors
- Check disk space
- Verify write permissions
- Check SQLite installation

## Next Steps

After successful testing:
1. Enable systemd service for auto-start
2. Set up log rotation
3. Configure cleanup schedules
4. Add monitoring/alerting
5. Customize for your use case

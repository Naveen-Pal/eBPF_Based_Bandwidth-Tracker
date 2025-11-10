"""
eBPF-based Per-Process Bandwidth Tracker
Monitors network usage per process with per-IP and protocol breakdown
"""

from bcc import BPF
import time
import argparse
from datetime import datetime
from collections import defaultdict
import signal
import sys
from storage import BandwidthStorage
import socket
import struct

# eBPF program code
BPF_PROGRAM = """
#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>

// Structure to hold bandwidth data
struct bandwidth_key_t {
    u32 pid;
    u32 remote_ip;
    u16 protocol;  // 0=TCP, 1=UDP
    u16 direction; // 0=TX, 1=RX
};

struct bandwidth_data_t {
    u64 bytes;
    u64 packets;
    u64 timestamp;
    char comm[TASK_COMM_LEN];
};

// Map to store bandwidth statistics
BPF_HASH(bandwidth_map, struct bandwidth_key_t, struct bandwidth_data_t);

// Helper function to get remote IP from socket
static u32 get_remote_ip(struct sock *sk) {
    u32 remote_ip = 0;
    u16 family = sk->__sk_common.skc_family;
    
    if (family == AF_INET) {
        remote_ip = sk->__sk_common.skc_daddr;
    }
    return remote_ip;
}

// TCP Send tracking
int trace_tcp_sendmsg(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg, size_t size) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    
    struct bandwidth_key_t key = {};
    key.pid = pid;
    key.remote_ip = get_remote_ip(sk);
    key.protocol = 0; // TCP
    key.direction = 0; // TX
    
    struct bandwidth_data_t *data = bandwidth_map.lookup(&key);
    if (data) {
        data->bytes += size;
        data->packets += 1;
        data->timestamp = bpf_ktime_get_ns();
    } else {
        struct bandwidth_data_t new_data = {};
        new_data.bytes = size;
        new_data.packets = 1;
        new_data.timestamp = bpf_ktime_get_ns();
        bpf_get_current_comm(&new_data.comm, sizeof(new_data.comm));
        bandwidth_map.update(&key, &new_data);
    }
    
    return 0;
}

// TCP Receive tracking
int trace_tcp_recvmsg(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg, 
                      size_t len, int nonblock, int flags, int *addr_len) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    
    struct bandwidth_key_t key = {};
    key.pid = pid;
    key.remote_ip = get_remote_ip(sk);
    key.protocol = 0; // TCP
    key.direction = 1; // RX
    
    struct bandwidth_data_t *data = bandwidth_map.lookup(&key);
    if (data) {
        data->bytes += len;
        data->packets += 1;
        data->timestamp = bpf_ktime_get_ns();
    } else {
        struct bandwidth_data_t new_data = {};
        new_data.bytes = len;
        new_data.packets = 1;
        new_data.timestamp = bpf_ktime_get_ns();
        bpf_get_current_comm(&new_data.comm, sizeof(new_data.comm));
        bandwidth_map.update(&key, &new_data);
    }
    
    return 0;
}

// UDP Send tracking
int trace_udp_sendmsg(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg, size_t size) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    
    struct bandwidth_key_t key = {};
    key.pid = pid;
    key.remote_ip = get_remote_ip(sk);
    key.protocol = 1; // UDP
    key.direction = 0; // TX
    
    struct bandwidth_data_t *data = bandwidth_map.lookup(&key);
    if (data) {
        data->bytes += size;
        data->packets += 1;
        data->timestamp = bpf_ktime_get_ns();
    } else {
        struct bandwidth_data_t new_data = {};
        new_data.bytes = size;
        new_data.packets = 1;
        new_data.timestamp = bpf_ktime_get_ns();
        bpf_get_current_comm(&new_data.comm, sizeof(new_data.comm));
        bandwidth_map.update(&key, &new_data);
    }
    
    return 0;
}

// UDP Receive tracking
int trace_udp_recvmsg(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg,
                      size_t len, int noblock, int flags, int *addr_len) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    
    struct bandwidth_key_t key = {};
    key.pid = pid;
    key.remote_ip = get_remote_ip(sk);
    key.protocol = 1; // UDP
    key.direction = 1; // RX
    
    struct bandwidth_data_t *data = bandwidth_map.lookup(&key);
    if (data) {
        data->bytes += len;
        data->packets += 1;
        data->timestamp = bpf_ktime_get_ns();
    } else {
        struct bandwidth_data_t new_data = {};
        new_data.bytes = len;
        new_data.packets = 1;
        new_data.timestamp = bpf_ktime_get_ns();
        bpf_get_current_comm(&new_data.comm, sizeof(new_data.comm));
        bandwidth_map.update(&key, &new_data);
    }
    
    return 0;
}
"""

class BandwidthTracker:
    def __init__(self, storage_db="bandwidth.db"):
        """Initialize the eBPF bandwidth tracker"""
        self.bpf = BPF(text=BPF_PROGRAM)
        self.storage = BandwidthStorage(storage_db)
        self.running = True
        
        # Attach kprobes
        self.bpf.attach_kprobe(event="tcp_sendmsg", fn_name="trace_tcp_sendmsg")
        self.bpf.attach_kprobe(event="tcp_recvmsg", fn_name="trace_tcp_recvmsg")
        self.bpf.attach_kprobe(event="udp_sendmsg", fn_name="trace_udp_sendmsg")
        self.bpf.attach_kprobe(event="udp_recvmsg", fn_name="trace_udp_recvmsg")
        
        print("eBPF program loaded successfully")
        print("Tracking network bandwidth per process...")
        
    def ip_to_str(self, ip):
        """Convert IP address from integer to string"""
        if ip == 0:
            return "0.0.0.0"
        return socket.inet_ntoa(struct.pack("<I", ip))
    
    def format_bytes(self, bytes):
        """Format bytes to human-readable format"""
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} PiB"
    
    def get_current_stats(self):
        """Get current bandwidth statistics from eBPF maps"""
        stats = defaultdict(lambda: {
            'tx_bytes': 0, 'rx_bytes': 0,
            'tx_packets': 0, 'rx_packets': 0,
            'tcp_tx': 0, 'tcp_rx': 0,
            'udp_tx': 0, 'udp_rx': 0,
            'remote_ips': defaultdict(lambda: {'tx': 0, 'rx': 0}),
            'comm': '',
            'pid': 0
        })
        
        bandwidth_map = self.bpf["bandwidth_map"]
        
        for key, value in bandwidth_map.items():
            pid = key.pid
            remote_ip = self.ip_to_str(key.remote_ip)
            protocol = "TCP" if key.protocol == 0 else "UDP"
            direction = "TX" if key.direction == 0 else "RX"
            
            comm = value.comm.decode('utf-8', 'replace')
            bytes_count = value.bytes
            packets_count = value.packets
            
            # Aggregate by process
            process_key = f"{pid}:{comm}"
            stats[process_key]['pid'] = pid
            stats[process_key]['comm'] = comm
            
            if direction == "TX":
                stats[process_key]['tx_bytes'] += bytes_count
                stats[process_key]['tx_packets'] += packets_count
                stats[process_key]['remote_ips'][remote_ip]['tx'] += bytes_count
                if protocol == "TCP":
                    stats[process_key]['tcp_tx'] += bytes_count
                else:
                    stats[process_key]['udp_tx'] += bytes_count
            else:
                stats[process_key]['rx_bytes'] += bytes_count
                stats[process_key]['rx_packets'] += packets_count
                stats[process_key]['remote_ips'][remote_ip]['rx'] += bytes_count
                if protocol == "TCP":
                    stats[process_key]['tcp_rx'] += bytes_count
                else:
                    stats[process_key]['udp_rx'] += bytes_count
        bandwidth_map.clear()
        return dict(stats)
    
    def print_stats(self, stats):
        """Print statistics in a formatted table"""
        print("\n" + "="*130)
        print(f"{'PID':<8} {'Process':<20} {'TX (Total)':<15} {'RX (Total)':<15} {'TCP TX':<12} {'TCP RX':<12} {'UDP TX':<12} {'UDP RX':<12} {'Remote IPs':<20}")
        print("="*130)
        
        # Sort by total bandwidth (TX + RX)
        sorted_stats = sorted(stats.items(), 
                            key=lambda x: x[1]['tx_bytes'] + x[1]['rx_bytes'], 
                            reverse=True)
        for process_key, data in sorted_stats[:20]:  # Top 20
            remote_ips_str = '|'.join(data['remote_ips'].keys()) if data['remote_ips'] else 'N/A'
            print(f"{data['pid']:<8} {data['comm']:<20} "
                  f"{self.format_bytes(data['tx_bytes']):<15} "
                  f"{self.format_bytes(data['rx_bytes']):<15} "
                  f"{self.format_bytes(data['tcp_tx']):<12} "
                  f"{self.format_bytes(data['tcp_rx']):<12} "
                  f"{self.format_bytes(data['udp_tx']):<12} "
                  f"{self.format_bytes(data['udp_rx']):<12} "
                  f"{remote_ips_str:<20}")
        print("="*130)
    
    def run(self, interval=1, web_mode=False):
        """Main loop to collect and display bandwidth statistics"""
        
        def signal_handler(sig, frame):
            print("\nShutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        last_stats = {}
        
        try:
            while self.running:
                time.sleep(interval)
                
                # Get current stats (these are deltas since last clear due to map.clear())
                current_stats = self.get_current_stats()
                
                # Calculate delta for display
                delta_stats = {}
                for key, current in current_stats.items():
                    # Since we clear the map, current_stats already contains deltas
                    # Calculate rate per second for display
                    delta_stats[key] = {
                        'pid': current['pid'],
                        'comm': current['comm'],
                        'tx_bytes': current['tx_bytes'] / interval,
                        'rx_bytes': current['rx_bytes'] / interval,
                        'tcp_tx': current['tcp_tx'] / interval,
                        'tcp_rx': current['tcp_rx'] / interval,
                        'udp_tx': current['udp_tx'] / interval,
                        'udp_rx': current['udp_rx'] / interval,
                        'tx_packets': current['tx_packets'],
                        'rx_packets': current['rx_packets'],
                        'remote_ips': current['remote_ips']
                    }
                
                # Store DELTAS in database (not accumulated values)
                timestamp = datetime.now()
                for key, data in current_stats.items():
                    # Only store if there was actual traffic
                    if data['tx_bytes'] > 0 or data['rx_bytes'] > 0:
                        # Store per-IP records with deltas
                        for remote_ip, ip_data in data['remote_ips'].items():
                            if ip_data['tx'] > 0 or ip_data['rx'] > 0:
                                # Determine dominant protocol for this IP
                                # Store TCP record if there's TCP traffic
                                if data['tcp_tx'] > 0 or data['tcp_rx'] > 0:
                                    self.storage.insert_bandwidth_record(
                                        timestamp=timestamp,
                                        pid=data['pid'],
                                        process_name=data['comm'],
                                        tx_bytes=ip_data['tx'],
                                        rx_bytes=ip_data['rx'],
                                        protocol='TCP',
                                        remote_ip=remote_ip
                                    )
                                # Store UDP record if there's UDP traffic
                                if data['udp_tx'] > 0 or data['udp_rx'] > 0:
                                    self.storage.insert_bandwidth_record(
                                        timestamp=timestamp,
                                        pid=data['pid'],
                                        process_name=data['comm'],
                                        tx_bytes=ip_data['tx'],
                                        rx_bytes=ip_data['rx'],
                                        protocol='UDP',
                                        remote_ip=remote_ip
                                    )
                
                # Print to console if not in web mode
                if not web_mode:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bandwidth Usage (Rate per second)")
                    self.print_stats(delta_stats)
                
                last_stats = current_stats
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.storage.close()

def main():
    parser = argparse.ArgumentParser(description="eBPF Per-Process Bandwidth Tracker")
    parser.add_argument("--interval", type=int, default=1, help="Update interval in seconds (default: 1)")
    parser.add_argument("--web", action="store_true", help="Run with web server")
    parser.add_argument("--db", type=str, default="bandwidth.db", help="SQLite database path")
    
    args = parser.parse_args()
    
    # Check if running as root
    import os
    if os.geteuid() != 0:
        print("Error: This program must be run as root (sudo)")
        sys.exit(1)
    
    tracker = BandwidthTracker(storage_db=args.db)
    
    if args.web:
        # Import and start web server in separate thread
        from web_server import start_web_server
        import threading
        
        web_thread = threading.Thread(target=start_web_server, args=(tracker,))
        web_thread.daemon = True
        web_thread.start()
        
        # print(f"Web server started at http://localhost:8080")
    
    tracker.run(interval=args.interval, web_mode=args.web)

if __name__ == "__main__":
    main()

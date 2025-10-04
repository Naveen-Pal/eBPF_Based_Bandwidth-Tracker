"""
Command-line interface for bandwidth tracker
Provides various views and reports
"""

import argparse
import sys
from storage import BandwidthStorage
from datetime import datetime, timedelta
from tabulate import tabulate

def format_bytes(bytes):
    """Format bytes to human-readable format"""
    if bytes is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"

def show_top_processes(storage, hours=1, top=10, protocol=None):
    """Display top processes by bandwidth usage"""
    print(f"\n{'='*80}")
    print(f"Top {top} Processes by Bandwidth (Last {hours} hour(s))")
    print(f"{'='*80}\n")
    
    processes = storage.get_top_processes(hours=hours, limit=top)
    
    if not processes:
        print("No data available for the specified time period.")
        return
    
    # Prepare table data
    table_data = []
    for i, proc in enumerate(processes, 1):
        table_data.append([
            i,
            proc['process_name'],
            format_bytes(proc['total_tx']),
            format_bytes(proc['total_rx']),
            format_bytes(proc['total_bandwidth']),
            proc['record_count']
        ])
    
    headers = ['#', 'Process', 'TX', 'RX', 'Total', 'Records']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    # Summary
    total_tx = sum(p['total_tx'] for p in processes)
    total_rx = sum(p['total_rx'] for p in processes)
    print(f"\nTotal TX: {format_bytes(total_tx)}")
    print(f"Total RX: {format_bytes(total_rx)}")
    print(f"Total Bandwidth: {format_bytes(total_tx + total_rx)}")

def show_protocol_breakdown(storage, hours=1):
    """Display bandwidth breakdown by protocol"""
    print(f"\n{'='*60}")
    print(f"Protocol Breakdown (Last {hours} hour(s))")
    print(f"{'='*60}\n")
    
    protocols = storage.get_protocol_breakdown(hours=hours)
    
    if not protocols:
        print("No protocol data available.")
        return
    
    # Prepare table data
    table_data = []
    for protocol, data in protocols.items():
        table_data.append([
            protocol,
            format_bytes(data['tx_bytes']),
            format_bytes(data['rx_bytes']),
            format_bytes(data['tx_bytes'] + data['rx_bytes'])
        ])
    
    headers = ['Protocol', 'TX', 'RX', 'Total']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))

def show_ip_breakdown(storage, process_name=None, hours=1, top=20):
    """Display bandwidth breakdown by remote IP"""
    if process_name:
        print(f"\n{'='*80}")
        print(f"IP Breakdown for '{process_name}' (Last {hours} hour(s))")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'='*80}")
        print(f"Top {top} Remote IPs by Bandwidth (Last {hours} hour(s))")
        print(f"{'='*80}\n")
    
    ips = storage.get_ip_breakdown(process_name=process_name, hours=hours)
    
    if not ips:
        print("No IP data available.")
        return
    
    # Prepare table data
    table_data = []
    for i, ip_data in enumerate(ips[:top], 1):
        table_data.append([
            i,
            ip_data['remote_ip'],
            ip_data.get('process_name', 'N/A'),
            format_bytes(ip_data['total_tx']),
            format_bytes(ip_data['total_rx']),
            format_bytes(ip_data['total_tx'] + ip_data['total_rx'])
        ])
    
    headers = ['#', 'Remote IP', 'Process', 'TX', 'RX', 'Total']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))

def show_process_history(storage, process_name, hours=24):
    """Display historical data for a specific process"""
    print(f"\n{'='*80}")
    print(f"History for '{process_name}' (Last {hours} hour(s))")
    print(f"{'='*80}\n")
    
    history = storage.get_process_history(process_name, hours=hours)
    
    if not history:
        print(f"No historical data found for process '{process_name}'.")
        return
    
    # Prepare table data (show last 20 entries)
    table_data = []
    for entry in history[:20]:
        table_data.append([
            entry['timestamp'],
            entry['pid'],
            entry['protocol'],
            format_bytes(entry['tx_bytes']),
            format_bytes(entry['rx_bytes']),
            format_bytes(entry['tx_bytes'] + entry['rx_bytes'])
        ])
    
    headers = ['Timestamp', 'PID', 'Protocol', 'TX', 'RX', 'Total']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    # Summary
    total_tx = sum(e['tx_bytes'] for e in history)
    total_rx = sum(e['rx_bytes'] for e in history)
    print(f"\nTotal records: {len(history)}")
    print(f"Total TX: {format_bytes(total_tx)}")
    print(f"Total RX: {format_bytes(total_rx)}")
    print(f"Total Bandwidth: {format_bytes(total_tx + total_rx)}")

def show_summary(storage, hours=1):
    """Display summary statistics"""
    print(f"\n{'='*60}")
    print(f"Summary Statistics (Last {hours} hour(s))")
    print(f"{'='*60}\n")
    
    stats = storage.get_summary_stats(hours=hours)
    
    print(f"Active Processes: {stats['process_count']}")
    print(f"Active PIDs: {stats['pid_count']}")
    print(f"Total Records: {stats['record_count']}")
    print(f"\nTotal TX: {format_bytes(stats['total_tx'] or 0)}")
    print(f"Total RX: {format_bytes(stats['total_rx'] or 0)}")
    print(f"Total Bandwidth: {format_bytes((stats['total_tx'] or 0) + (stats['total_rx'] or 0))}")

def live_monitor(storage, interval=2, top=10):
    """Live monitoring mode (reads from database)"""
    import time
    import os
    
    print("Live Monitoring Mode (Press Ctrl+C to exit)")
    print(f"Update interval: {interval} seconds\n")
    
    try:
        while True:
            # Clear screen
            os.system('clear' if os.name != 'nt' else 'cls')
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
            show_top_processes(storage, hours=1, top=top)
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\nExiting live monitor...")

def main():
    parser = argparse.ArgumentParser(
        description="CLI for eBPF Bandwidth Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show top 10 processes from last hour
  sudo python3 cli.py --top 10 --hours 1
  
  # Show protocol breakdown
  sudo python3 cli.py --protocol-breakdown
  
  # Show IP breakdown for a specific process
  sudo python3 cli.py --ip-breakdown --process firefox
  
  # Show history for a process
  sudo python3 cli.py --history --process chrome --hours 24
  
  # Live monitoring
  sudo python3 cli.py --live --interval 2
        """
    )
    
    parser.add_argument("--db", type=str, default="bandwidth.db",
                       help="Path to SQLite database (default: bandwidth.db)")
    parser.add_argument("--hours", type=int, default=1,
                       help="Time window in hours (default: 1)")
    parser.add_argument("--top", type=int, default=10,
                       help="Number of top entries to show (default: 10)")
    
    # Display modes
    parser.add_argument("--live", action="store_true",
                       help="Live monitoring mode")
    parser.add_argument("--history", action="store_true",
                       help="Show historical data")
    parser.add_argument("--protocol-breakdown", action="store_true",
                       help="Show protocol breakdown")
    parser.add_argument("--ip-breakdown", action="store_true",
                       help="Show IP breakdown")
    parser.add_argument("--summary", action="store_true",
                       help="Show summary statistics")
    
    # Filters
    parser.add_argument("--process", type=str,
                       help="Filter by process name")
    parser.add_argument("--protocol", type=str, choices=['tcp', 'udp'],
                       help="Filter by protocol")
    
    # Options
    parser.add_argument("--interval", type=int, default=2,
                       help="Update interval for live mode (default: 2)")
    parser.add_argument("--cleanup", type=int,
                       help="Clean up records older than N days")
    
    args = parser.parse_args()
    
    # Initialize storage
    try:
        storage = BandwidthStorage(args.db)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)
    
    try:
        # Cleanup mode
        if args.cleanup:
            print(f"Cleaning up records older than {args.cleanup} days...")
            storage.cleanup_old_records(days=args.cleanup)
            print("Cleanup completed.")
            return
        
        # Live mode
        if args.live:
            live_monitor(storage, interval=args.interval, top=args.top)
            return
        
        # History mode
        if args.history:
            if args.process:
                show_process_history(storage, args.process, hours=args.hours)
            else:
                show_top_processes(storage, hours=args.hours, top=args.top)
            return
        
        # Protocol breakdown
        if args.protocol_breakdown:
            show_protocol_breakdown(storage, hours=args.hours)
            return
        
        # IP breakdown
        if args.ip_breakdown:
            show_ip_breakdown(storage, process_name=args.process, 
                            hours=args.hours, top=args.top)
            return
        
        # Summary
        if args.summary:
            show_summary(storage, hours=args.hours)
            return
        
        # Default: show top processes
        show_top_processes(storage, hours=args.hours, top=args.top, 
                          protocol=args.protocol)
        
    finally:
        storage.close()

if __name__ == "__main__":
    main()

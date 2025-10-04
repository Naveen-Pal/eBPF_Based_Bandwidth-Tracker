"""
Example script demonstrating how to use the bandwidth tracker programmatically
"""

from storage import BandwidthStorage
from datetime import datetime, timedelta
import time


def example_query_api():
    """Example: Query bandwidth data programmatically"""
    print("="*60)
    print("Example: Querying Bandwidth Data")
    print("="*60)
    
    # Connect to database
    storage = BandwidthStorage("bandwidth.db")
    
    # 1. Get top processes from last hour
    print("\n1. Top 5 Processes (Last Hour):")
    print("-" * 60)
    top_processes = storage.get_top_processes(hours=1, limit=5)
    for proc in top_processes:
        print(f"  {proc['process_name']:20s} - "
              f"TX: {proc['total_tx']:>12,} bytes, "
              f"RX: {proc['total_rx']:>12,} bytes")
    
    # 2. Get protocol breakdown
    print("\n2. Protocol Breakdown:")
    print("-" * 60)
    protocols = storage.get_protocol_breakdown(hours=1)
    for protocol, data in protocols.items():
        print(f"  {protocol}: "
              f"TX={data['tx_bytes']:,} bytes, "
              f"RX={data['rx_bytes']:,} bytes")
    
    # 3. Get summary statistics
    print("\n3. Summary Statistics:")
    print("-" * 60)
    summary = storage.get_summary_stats(hours=24)
    print(f"  Active Processes: {summary['process_count']}")
    print(f"  Total TX: {summary['total_tx']:,} bytes")
    print(f"  Total RX: {summary['total_rx']:,} bytes")
    print(f"  Record Count: {summary['record_count']}")
    
    # 4. Get time series data
    print("\n4. Time Series Data (Last Hour, 5-min intervals):")
    print("-" * 60)
    timeseries = storage.get_time_series(hours=1, interval_minutes=5)
    for point in timeseries[-5:]:  # Last 5 data points
        timestamp = datetime.fromisoformat(point['timestamp'])
        print(f"  {timestamp.strftime('%H:%M:%S')} - "
              f"TX: {point['tx_bytes']:>8,} bytes, "
              f"RX: {point['rx_bytes']:>8,} bytes")
    
    storage.close()


def example_monitor_process():
    """Example: Monitor specific process bandwidth"""
    print("\n" + "="*60)
    print("Example: Monitoring Specific Process")
    print("="*60)
    
    storage = BandwidthStorage("bandwidth.db")
    process_name = "firefox"  # Change to any process you want to monitor
    
    print(f"\nMonitoring '{process_name}' (Last 24 hours):")
    print("-" * 60)
    
    history = storage.get_process_history(process_name, hours=24)
    
    if not history:
        print(f"  No data found for '{process_name}'")
    else:
        print(f"  Total records: {len(history)}")
        
        # Calculate totals
        total_tx = sum(h['tx_bytes'] for h in history)
        total_rx = sum(h['rx_bytes'] for h in history)
        
        print(f"  Total TX: {total_tx:,} bytes")
        print(f"  Total RX: {total_rx:,} bytes")
        print(f"  Total Bandwidth: {total_tx + total_rx:,} bytes")
        
        # Show recent activity
        print("\n  Recent activity:")
        for entry in history[:5]:
            print(f"    {entry['timestamp']} - "
                  f"PID: {entry['pid']}, "
                  f"TX: {entry['tx_bytes']:,}, "
                  f"RX: {entry['rx_bytes']:,}")
    
    storage.close()


def example_ip_analysis():
    """Example: Analyze traffic by remote IP"""
    print("\n" + "="*60)
    print("Example: Remote IP Analysis")
    print("="*60)
    
    storage = BandwidthStorage("bandwidth.db")
    
    print("\nTop 10 Remote IPs (Last Hour):")
    print("-" * 60)
    
    ips = storage.get_ip_breakdown(hours=1)
    
    if not ips:
        print("  No IP data available")
    else:
        for idx, ip_data in enumerate(ips[:10], 1):
            print(f"  {idx}. {ip_data['remote_ip']:15s} - "
                  f"TX: {ip_data['total_tx']:>12,} bytes, "
                  f"RX: {ip_data['total_rx']:>12,} bytes")
    
    storage.close()


def example_custom_query():
    """Example: Custom SQL query"""
    print("\n" + "="*60)
    print("Example: Custom SQL Query")
    print("="*60)
    
    storage = BandwidthStorage("bandwidth.db")
    
    # Custom query: Find processes with high TX/RX ratio
    print("\nProcesses with high upload ratio (TX > 2 * RX):")
    print("-" * 60)
    
    storage.cursor.execute("""
        SELECT 
            process_name,
            SUM(tx_bytes) as total_tx,
            SUM(rx_bytes) as total_rx,
            CAST(SUM(tx_bytes) AS FLOAT) / NULLIF(SUM(rx_bytes), 0) as ratio
        FROM bandwidth_records
        WHERE timestamp >= datetime('now', '-1 hour')
        GROUP BY process_name
        HAVING total_tx > 2 * total_rx
        ORDER BY ratio DESC
        LIMIT 10
    """)
    
    results = storage.cursor.fetchall()
    for row in results:
        print(f"  {row['process_name']:20s} - "
              f"Ratio: {row['ratio']:.2f}, "
              f"TX: {row['total_tx']:,}, "
              f"RX: {row['total_rx']:,}")
    
    if not results:
        print("  No processes match the criteria")
    
    storage.close()


def example_export_data():
    """Example: Export data to JSON"""
    print("\n" + "="*60)
    print("Example: Export Data to JSON")
    print("="*60)
    
    import json
    
    storage = BandwidthStorage("bandwidth.db")
    
    # Get data
    data = {
        'timestamp': datetime.now().isoformat(),
        'summary': storage.get_summary_stats(hours=1),
        'top_processes': storage.get_top_processes(hours=1, limit=10),
        'protocols': storage.get_protocol_breakdown(hours=1)
    }
    
    # Save to file
    output_file = 'bandwidth_export.json'
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n  Data exported to: {output_file}")
    print(f"  File size: {os.path.getsize(output_file):,} bytes")
    
    storage.close()


def main():
    """Run all examples"""
    import os
    
    # Check if database exists
    if not os.path.exists("bandwidth.db"):
        print("Error: bandwidth.db not found!")
        print("Please run the tracker first to collect some data:")
        print("  sudo python3 ebpf_tracker.py")
        return
    
    # Run examples
    try:
        example_query_api()
        example_monitor_process()
        example_ip_analysis()
        example_custom_query()
        example_export_data()
        
        print("\n" + "="*60)
        print("Examples completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

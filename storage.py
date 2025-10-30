"""
SQLite storage layer for bandwidth tracking data
Handles persistence and historical queries
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

class BandwidthStorage:
    def __init__(self, db_path="bandwidth.db"):
        """Initialize SQLite database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary database tables"""
        cursor = self.conn.cursor()
        # Main bandwidth records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bandwidth_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                pid INTEGER NOT NULL,
                process_name TEXT NOT NULL,
                tx_bytes INTEGER NOT NULL,
                rx_bytes INTEGER NOT NULL,
                protocol TEXT NOT NULL,
                remote_ip TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON bandwidth_records(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_process 
            ON bandwidth_records(process_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pid 
            ON bandwidth_records(pid)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_remote_ip 
        ON bandwidth_records(remote_ip)
        """)
        
        # # Per-IP tracking table
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS ip_bandwidth (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         timestamp DATETIME NOT NULL,
        #         pid INTEGER NOT NULL,
        #         process_name TEXT NOT NULL,
        #         remote_ip TEXT NOT NULL,
        #         tx_bytes INTEGER NOT NULL,
        #         rx_bytes INTEGER NOT NULL,
        #         protocol TEXT NOT NULL,
        #         created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        #     )
        # """)
        
        # Aggregated statistics table (for faster queries)
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS hourly_stats (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         hour_start DATETIME NOT NULL,
        #         process_name TEXT NOT NULL,
        #         total_tx_bytes INTEGER NOT NULL,
        #         total_rx_bytes INTEGER NOT NULL,
        #         tcp_tx_bytes INTEGER NOT NULL,
        #         tcp_rx_bytes INTEGER NOT NULL,
        #         udp_tx_bytes INTEGER NOT NULL,
        #         udp_rx_bytes INTEGER NOT NULL,
        #         created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        #         UNIQUE(hour_start, process_name)
        #     )
        # """)
        
        self.conn.commit()
        cursor.close()
    
    def insert_bandwidth_record(self, timestamp: datetime, pid: int, 
                               process_name: str, tx_bytes: int, 
                               rx_bytes: int, protocol: str, 
                               remote_ip: str = None):
        """Insert a bandwidth record"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO bandwidth_records 
                (timestamp, pid, process_name, tx_bytes, rx_bytes, protocol, remote_ip)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, pid, process_name, tx_bytes, rx_bytes, protocol, remote_ip))
            self.conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Error inserting record: {e}")
    
    def insert_ip_bandwidth(self, timestamp: datetime, pid: int,
                          process_name: str, remote_ip: str,
                          tx_bytes: int, rx_bytes: int, protocol: str):
        """Insert per-IP bandwidth record"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO bandwidth_records
                (timestamp, pid, process_name, remote_ip, tx_bytes, rx_bytes, protocol)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, pid, process_name, remote_ip, tx_bytes, rx_bytes, protocol))
            self.conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Error inserting IP record: {e}")
    
    def get_top_processes(self, hours: int = 1, limit: int = 10) -> List[Dict]:
        """Get top processes by average bandwidth usage in the last N hours"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                process_name,
                SUM(tx_bytes) as total_tx,
                SUM(rx_bytes) as total_rx,
                SUM(tx_bytes + rx_bytes) as total_bandwidth,
                COUNT(*) as record_count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM bandwidth_records
            WHERE timestamp >= ?
            GROUP BY process_name
            ORDER BY total_bandwidth DESC
            LIMIT ?
        """, (start_time, limit))
        
        results = []
        for row in cursor.fetchall():
            # Calculate time span for average rate
            first = datetime.fromisoformat(row['first_seen'])
            last = datetime.fromisoformat(row['last_seen'])
            time_span = max((last - first).total_seconds(), hours * 3600)
            
            results.append({
                'process_name': row['process_name'],
                'total_tx': row['total_tx'] / time_span,  # bytes per second (average)
                'total_rx': row['total_rx'] / time_span,
                'total_bandwidth': row['total_bandwidth'] / time_span,
                'record_count': row['record_count']
            })
        
        cursor.close()
        return results
    
    def get_process_history(self, process_name: str, hours: int = 24) -> List[Dict]:
        """Get historical bandwidth data for a specific process"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                timestamp,
                pid,
                tx_bytes,
                rx_bytes,
                protocol
            FROM bandwidth_records
            WHERE process_name = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        """, (process_name, start_time))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'timestamp': row['timestamp'],
                'pid': row['pid'],
                'tx_bytes': row['tx_bytes'],
                'rx_bytes': row['rx_bytes'],
                'protocol': row['protocol']
            })
        
        cursor.close()
        return results
    
    def get_protocol_breakdown(self, hours: int = 1) -> Dict:
        """Get bandwidth breakdown by protocol (average rate over time period)"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                protocol,
                SUM(tx_bytes) as total_tx,
                SUM(rx_bytes) as total_rx,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM bandwidth_records
            WHERE timestamp >= ? AND protocol != 'TOTAL'
            GROUP BY protocol
        """, (start_time,))
        
        results = {}
        for row in cursor.fetchall():
            # Calculate time span for average rate
            first = datetime.fromisoformat(row['first_seen'])
            last = datetime.fromisoformat(row['last_seen'])
            time_span = max((last - first).total_seconds(), hours * 3600)  # Use window as minimum
            
            results[row['protocol']] = {
                'tx_bytes': row['total_tx'] / time_span,  # bytes per second (average)
                'rx_bytes': row['total_rx'] / time_span
            }
        
        cursor.close()
        return results
    
    def get_protocol_breakdown_realtime(self, seconds: int = 60) -> Dict:
        """Get real-time bandwidth breakdown by protocol (current rate)"""
        start_time = datetime.now() - timedelta(seconds=seconds)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                protocol,
                SUM(tx_bytes) as total_tx,
                SUM(rx_bytes) as total_rx,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM bandwidth_records
            WHERE timestamp >= ?
            GROUP BY protocol
        """, (start_time,))
        
        results = {}
        for row in cursor.fetchall():
            # Calculate time span for rate calculation
            first = datetime.fromisoformat(row['first_seen'])
            last = datetime.fromisoformat(row['last_seen'])
            time_span = max((last - first).total_seconds(), seconds)
            
            results[row['protocol']] = {
                'tx_rate': row['total_tx'] / time_span,  # bytes per second
                'rx_rate': row['total_rx'] / time_span
            }
        
        cursor.close()
        return results
    
    def get_ip_breakdown(self, process_name: str = None, hours: int = 1) -> List[Dict]:
        """Get bandwidth breakdown by remote IP (average rate over time period)"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor = self.conn.cursor()
        if process_name:
            cursor.execute("""
                SELECT 
                    remote_ip,
                    process_name,
                    SUM(tx_bytes) as total_tx,
                    SUM(rx_bytes) as total_rx,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen
                FROM bandwidth_records
                WHERE timestamp >= ? AND process_name = ? AND remote_ip IS NOT NULL
                GROUP BY remote_ip, process_name
                ORDER BY (total_tx + total_rx) DESC
            """, (start_time, process_name))
        else:
            cursor.execute("""
                SELECT 
                    remote_ip,
                    SUM(tx_bytes) as total_tx,
                    SUM(rx_bytes) as total_rx,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen
                FROM bandwidth_records
                WHERE timestamp >= ? AND remote_ip IS NOT NULL
                GROUP BY remote_ip
                ORDER BY (total_tx + total_rx) DESC
                LIMIT 20
            """, (start_time,))
        
        results = []
        for row in cursor.fetchall():
            # Calculate time span for average rate
            first = datetime.fromisoformat(row['first_seen'])
            last = datetime.fromisoformat(row['last_seen'])
            time_span = max((last - first).total_seconds(), hours * 3600)
            
            result_dict = {
                'remote_ip': row['remote_ip'],
                'total_tx': row['total_tx'] / time_span,  # bytes per second (average)
                'total_rx': row['total_rx'] / time_span
            }
            # Only add process_name if it exists in the row
            if process_name:
                result_dict['process_name'] = row['process_name']
            else:
                result_dict['process_name'] = 'N/A'
            
            results.append(result_dict)
        
        cursor.close()
        return results
    
    def get_ip_breakdown_realtime(self, process_name: str = None, seconds: int = 60) -> List[Dict]:
        """Get real-time bandwidth breakdown by remote IP (current rate)"""
        start_time = datetime.now() - timedelta(seconds=seconds)
        
        cursor = self.conn.cursor()
        if process_name:
            cursor.execute("""
                SELECT 
                    remote_ip,
                    process_name,
                    SUM(tx_bytes) as total_tx,
                    SUM(rx_bytes) as total_rx,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen
                FROM bandwidth_records
                WHERE timestamp >= ? AND process_name = ? AND remote_ip IS NOT NULL
                GROUP BY remote_ip, process_name
                ORDER BY (total_tx + total_rx) DESC
            """, (start_time, process_name))
        else:
            cursor.execute("""
                SELECT 
                    remote_ip,
                    SUM(tx_bytes) as total_tx,
                    SUM(rx_bytes) as total_rx,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen
                FROM bandwidth_records
                WHERE timestamp >= ? AND remote_ip IS NOT NULL
                GROUP BY remote_ip
                ORDER BY (total_tx + total_rx) DESC
                LIMIT 20
            """, (start_time,))
        
        results = []
        for row in cursor.fetchall():
            # Calculate time span for rate calculation
            first = datetime.fromisoformat(row['first_seen'])
            last = datetime.fromisoformat(row['last_seen'])
            time_span = max((last - first).total_seconds(), seconds)
            
            result_dict = {
                'remote_ip': row['remote_ip'],
                'tx_rate': row['total_tx'] / time_span,  # bytes per second
                'rx_rate': row['total_rx'] / time_span
            }
            if process_name:
                result_dict['process_name'] = row['process_name']
            else:
                result_dict['process_name'] = 'N/A'
            
            results.append(result_dict)
        
        cursor.close()
        return results
    
    def get_active_processes(self, hours: int = 1) -> List[str]:
        """Get list of active processes in the time window"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT process_name
            FROM bandwidth_records
            WHERE timestamp >= ?
            ORDER BY process_name
        """, (start_time,))
        
        results = [row['process_name'] for row in cursor.fetchall()]
        cursor.close()
        return results
    
    def get_time_series(self, process_name: str = None, hours: int = 1, interval_minutes: int = 5) -> List[Dict]:
        """Get time series data for visualization with rate calculations"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor = self.conn.cursor()
        # Get data grouped by time intervals
        if process_name:
            cursor.execute("""
                SELECT 
                    timestamp,
                    tx_bytes,
                    rx_bytes
                FROM bandwidth_records
                WHERE timestamp >= ? AND process_name = ?
                ORDER BY timestamp
            """, (start_time, process_name))
        else:
            cursor.execute("""
                SELECT 
                    timestamp,
                    SUM(tx_bytes) as tx_bytes,
                    SUM(rx_bytes) as rx_bytes
                FROM bandwidth_records
                WHERE timestamp >= ?
                GROUP BY timestamp
                ORDER BY timestamp
            """, (start_time,))
        
        # Bucket data by interval
        results = []
        current_bucket = None
        bucket_data = {'tx': 0, 'rx': 0, 'count': 0, 'start_time': None, 'end_time': None}
        
        for row in cursor.fetchall():
            timestamp = datetime.fromisoformat(row['timestamp'])
            bucket_time = timestamp.replace(second=0, microsecond=0)
            bucket_time = bucket_time.replace(minute=(bucket_time.minute // interval_minutes) * interval_minutes)
            
            if current_bucket is None:
                current_bucket = bucket_time
                bucket_data['start_time'] = timestamp
            
            if bucket_time != current_bucket:
                # Save current bucket (calculate rate)
                if bucket_data['count'] > 0 and bucket_data['start_time'] and bucket_data['end_time']:
                    time_span = (bucket_data['end_time'] - bucket_data['start_time']).total_seconds()
                    if time_span == 0:
                        time_span = interval_minutes * 60  # Use interval as fallback
                    
                    results.append({
                        'timestamp': current_bucket.isoformat(),
                        'tx_bytes': bucket_data['tx'] / time_span,  # Rate in bytes/second
                        'rx_bytes': bucket_data['rx'] / time_span
                    })
                # Reset for new bucket
                current_bucket = bucket_time
                bucket_data = {'tx': 0, 'rx': 0, 'count': 0, 'start_time': timestamp, 'end_time': timestamp}
            
            bucket_data['tx'] += row['tx_bytes']
            bucket_data['rx'] += row['rx_bytes']
            bucket_data['count'] += 1
            bucket_data['end_time'] = timestamp
        
        # Add last bucket
        if bucket_data['count'] > 0 and bucket_data['start_time'] and bucket_data['end_time']:
            time_span = (bucket_data['end_time'] - bucket_data['start_time']).total_seconds()
            if time_span == 0:
                time_span = interval_minutes * 60
            
            results.append({
                'timestamp': current_bucket.isoformat(),
                'tx_bytes': bucket_data['tx'] / time_span,
                'rx_bytes': bucket_data['rx'] / time_span
            })
        
        cursor.close()
        return results
    
    def cleanup_old_records(self, days: int = 7):
        """Delete records older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM bandwidth_records WHERE timestamp < ?
        """, (cutoff_date,))
        
        # cursor.execute("""
        #     DELETE FROM ip_bandwidth WHERE timestamp < ?
        # """, (cutoff_date,))
        
        self.conn.commit()
        cursor.close()
        print(f"Cleaned up records older than {days} days")
    
    def get_summary_stats(self, hours: int = 1) -> Dict:
        """Get summary statistics (average bandwidth rate over time period)"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT process_name) as process_count,
                COUNT(DISTINCT pid) as pid_count,
                SUM(tx_bytes) as total_tx,
                SUM(rx_bytes) as total_rx,
                COUNT(*) as record_count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM bandwidth_records
            WHERE timestamp >= ?
        """, (start_time,))
        
        row = cursor.fetchone()
        
        # Calculate time span for average rate
        if row['first_seen'] and row['last_seen']:
            first = datetime.fromisoformat(row['first_seen'])
            last = datetime.fromisoformat(row['last_seen'])
            time_span = max((last - first).total_seconds(), hours * 3600)
        else:
            time_span = hours * 3600
        
        result = {
            'process_count': row['process_count'],
            'pid_count': row['pid_count'],
            'total_tx': (row['total_tx'] or 0) / time_span,  # bytes per second (average)
            'total_rx': (row['total_rx'] or 0) / time_span,
            'record_count': row['record_count']
        }
        cursor.close()
        return result
    
    def get_summary_stats_realtime(self, seconds: int = 60) -> Dict:
        """Get real-time summary statistics (current bandwidth rate)"""
        start_time = datetime.now() - timedelta(seconds=seconds)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT process_name) as process_count,
                COUNT(DISTINCT pid) as pid_count,
                SUM(tx_bytes) as total_tx,
                SUM(rx_bytes) as total_rx,
                COUNT(*) as record_count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM bandwidth_records
            WHERE timestamp >= ?
        """, (start_time,))
        
        row = cursor.fetchone()
        
        # Calculate time span for rate calculation
        if row['first_seen'] and row['last_seen']:
            first = datetime.fromisoformat(row['first_seen'])
            last = datetime.fromisoformat(row['last_seen'])
            time_span = max((last - first).total_seconds(), seconds)
        else:
            time_span = seconds
        
        result = {
            'process_count': row['process_count'],
            'pid_count': row['pid_count'],
            'total_tx': (row['total_tx'] or 0) / time_span,  # bytes per second
            'total_rx': (row['total_rx'] or 0) / time_span,
            'record_count': row['record_count']
        }
        cursor.close()
        return result
    
    def get_current_rate(self, seconds: int = 60) -> List[Dict]:
        """Get current bandwidth rate (bytes/second) from recent data
        
        Since we store deltas in the database, we calculate the rate by
        summing recent deltas over a time window.
        """
        start_time = datetime.now() - timedelta(seconds=seconds)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                pid,
                process_name,
                SUM(CASE WHEN protocol = 'TCP' THEN tx_bytes ELSE 0 END) as tcp_tx,
                SUM(CASE WHEN protocol = 'TCP' THEN rx_bytes ELSE 0 END) as tcp_rx,
                SUM(CASE WHEN protocol = 'UDP' THEN tx_bytes ELSE 0 END) as udp_tx,
                SUM(CASE WHEN protocol = 'UDP' THEN rx_bytes ELSE 0 END) as udp_rx,
                SUM(tx_bytes) as total_tx,
                SUM(rx_bytes) as total_rx,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM bandwidth_records
            WHERE timestamp >= ?
            GROUP BY pid, process_name
            HAVING total_tx > 0 OR total_rx > 0
            ORDER BY (total_tx + total_rx) DESC
        """, (start_time,))
        
        results = []
        for row in cursor.fetchall():
            # Calculate time span for rate calculation
            first = datetime.fromisoformat(row['first_seen'])
            last = datetime.fromisoformat(row['last_seen'])
            time_span = max((last - first).total_seconds(), seconds)  # Use window size as minimum
            
            # Calculate rate = total bytes / time window
            results.append({
                'pid': row['pid'],
                'process_name': row['process_name'],
                'tx_rate': row['total_tx'] / time_span,
                'rx_rate': row['total_rx'] / time_span,
                'tcp_tx_rate': row['tcp_tx'] / time_span,
                'tcp_rx_rate': row['tcp_rx'] / time_span,
                'udp_tx_rate': row['udp_tx'] / time_span,
                'udp_rx_rate': row['udp_rx'] / time_span,
            })
        
        cursor.close()
        return results
    
    def close(self):
        """Close database connection"""
        self.conn.close()

# Test the storage module
if __name__ == "__main__":
    storage = BandwidthStorage("test_bandwidth.db")
    
    # Insert test data
    now = datetime.now()
    storage.insert_bandwidth_record(now, 1234, "firefox", 1024*1024, 512*1024, "TCP")
    storage.insert_bandwidth_record(now, 1235, "chrome", 2048*1024, 1024*1024, "TCP")
    
    # Query data
    print("Top processes:")
    for proc in storage.get_top_processes(hours=1):
        print(f"  {proc['process_name']}: TX={proc['total_tx']}, RX={proc['total_rx']}")
    
    print("\nSummary stats:")
    print(storage.get_summary_stats(hours=1))
    
    storage.close()

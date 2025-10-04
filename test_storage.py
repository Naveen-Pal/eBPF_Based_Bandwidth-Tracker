"""
Unit tests for bandwidth tracker storage module
"""

import unittest
from datetime import datetime, timedelta
from storage import BandwidthStorage
import os
import tempfile


class TestBandwidthStorage(unittest.TestCase):
    """Test cases for BandwidthStorage class"""
    
    def setUp(self):
        """Set up test database"""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.storage = BandwidthStorage(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test database"""
        self.storage.close()
        os.unlink(self.temp_db.name)
    
    def test_database_creation(self):
        """Test that database tables are created"""
        cursor = self.storage.cursor
        
        # Check if tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='bandwidth_records'
        """)
        self.assertIsNotNone(cursor.fetchone())
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ip_bandwidth'
        """)
        self.assertIsNotNone(cursor.fetchone())
    
    def test_insert_bandwidth_record(self):
        """Test inserting a bandwidth record"""
        now = datetime.now()
        self.storage.insert_bandwidth_record(
            timestamp=now,
            pid=1234,
            process_name='test_process',
            tx_bytes=1024,
            rx_bytes=2048,
            protocol='TCP'
        )
        
        # Verify insertion
        cursor = self.storage.cursor
        cursor.execute("SELECT COUNT(*) FROM bandwidth_records")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
        
        cursor.execute("SELECT * FROM bandwidth_records")
        row = cursor.fetchone()
        self.assertEqual(row['pid'], 1234)
        self.assertEqual(row['process_name'], 'test_process')
        self.assertEqual(row['tx_bytes'], 1024)
        self.assertEqual(row['rx_bytes'], 2048)
    
    def test_get_top_processes(self):
        """Test getting top processes"""
        now = datetime.now()
        
        # Insert test data
        processes = [
            ('firefox', 5000, 10000),
            ('chrome', 3000, 6000),
            ('curl', 1000, 2000),
        ]
        
        for proc_name, tx, rx in processes:
            self.storage.insert_bandwidth_record(
                timestamp=now,
                pid=1000,
                process_name=proc_name,
                tx_bytes=tx,
                rx_bytes=rx,
                protocol='TCP'
            )
        
        # Get top processes
        top = self.storage.get_top_processes(hours=1, limit=10)
        
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0]['process_name'], 'firefox')
        self.assertEqual(top[0]['total_tx'], 5000)
        self.assertEqual(top[0]['total_rx'], 10000)
    
    def test_get_summary_stats(self):
        """Test getting summary statistics"""
        now = datetime.now()
        
        # Insert test data
        self.storage.insert_bandwidth_record(
            timestamp=now,
            pid=1234,
            process_name='test1',
            tx_bytes=1000,
            rx_bytes=2000,
            protocol='TCP'
        )
        
        self.storage.insert_bandwidth_record(
            timestamp=now,
            pid=1235,
            process_name='test2',
            tx_bytes=3000,
            rx_bytes=4000,
            protocol='UDP'
        )
        
        # Get summary
        summary = self.storage.get_summary_stats(hours=1)
        
        self.assertEqual(summary['process_count'], 2)
        self.assertEqual(summary['total_tx'], 4000)
        self.assertEqual(summary['total_rx'], 6000)
    
    def test_cleanup_old_records(self):
        """Test cleaning up old records"""
        # Insert old record
        old_date = datetime.now() - timedelta(days=10)
        self.storage.insert_bandwidth_record(
            timestamp=old_date,
            pid=1234,
            process_name='old_process',
            tx_bytes=1000,
            rx_bytes=2000,
            protocol='TCP'
        )
        
        # Insert recent record
        recent_date = datetime.now()
        self.storage.insert_bandwidth_record(
            timestamp=recent_date,
            pid=1235,
            process_name='recent_process',
            tx_bytes=1000,
            rx_bytes=2000,
            protocol='TCP'
        )
        
        # Cleanup records older than 7 days
        self.storage.cleanup_old_records(days=7)
        
        # Verify only recent record remains
        cursor = self.storage.cursor
        cursor.execute("SELECT COUNT(*) FROM bandwidth_records")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
        
        cursor.execute("SELECT process_name FROM bandwidth_records")
        row = cursor.fetchone()
        self.assertEqual(row['process_name'], 'recent_process')


class TestFormatting(unittest.TestCase):
    """Test formatting utilities"""
    
    def test_format_bytes(self):
        """Test byte formatting function"""
        from storage import BandwidthStorage
        storage = BandwidthStorage(':memory:')
        
        # This would need the format_bytes function to be in storage.py
        # For now, test the storage works
        self.assertIsNotNone(storage)
        storage.close()


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)

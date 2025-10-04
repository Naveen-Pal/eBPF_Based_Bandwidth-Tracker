"""
Flask web server for bandwidth tracker visualization
Provides REST API and serves web UI
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from storage import BandwidthStorage
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__, static_folder='static')
CORS(app)

# Global tracker instance (will be set when starting)
tracker_instance = None
storage_instance = None

def format_bytes(bytes):
    """Format bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"

@app.route('/')
def index():
    """Serve the main web UI"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, etc.)"""
    return send_from_directory('static', filename)

@app.route('/api/current')
def get_current_stats():
    """Get current real-time bandwidth statistics"""
    if tracker_instance is None:
        return jsonify({'error': 'Tracker not initialized'}), 500
    
    try:
        stats = tracker_instance.get_current_stats()
        
        # Convert to list format for JSON
        results = []
        for key, data in stats.items():
            results.append({
                'pid': data['pid'],
                'process_name': data['comm'],
                'tx_bytes': data['tx_bytes'],
                'rx_bytes': data['rx_bytes'],
                'tcp_tx': data['tcp_tx'],
                'tcp_rx': data['tcp_rx'],
                'udp_tx': data['udp_tx'],
                'udp_rx': data['udp_rx'],
                'tx_formatted': format_bytes(data['tx_bytes']),
                'rx_formatted': format_bytes(data['rx_bytes']),
                'total_bytes': data['tx_bytes'] + data['rx_bytes'],
                'total_formatted': format_bytes(data['tx_bytes'] + data['rx_bytes'])
            })
        
        # Sort by total bandwidth
        results.sort(key=lambda x: x['total_bytes'], reverse=True)
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'processes': results[:50]  # Top 50
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/top')
def get_top_processes():
    """Get top processes from historical data"""
    hours = request.args.get('hours', default=1, type=int)
    limit = request.args.get('limit', default=10, type=int)
    
    try:
        results = storage_instance.get_top_processes(hours=hours, limit=limit)
        
        # Format the results
        for result in results:
            result['total_tx_formatted'] = format_bytes(result['total_tx'])
            result['total_rx_formatted'] = format_bytes(result['total_rx'])
            result['total_bandwidth_formatted'] = format_bytes(result['total_bandwidth'])
        
        return jsonify({
            'hours': hours,
            'processes': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/process/<process_name>')
def get_process_history(process_name):
    """Get historical data for a specific process"""
    hours = request.args.get('hours', default=24, type=int)
    
    try:
        results = storage_instance.get_process_history(process_name, hours=hours)
        
        return jsonify({
            'process_name': process_name,
            'hours': hours,
            'history': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/protocol/breakdown')
def get_protocol_breakdown():
    """Get bandwidth breakdown by protocol"""
    hours = request.args.get('hours', default=1, type=int)
    
    try:
        results = storage_instance.get_protocol_breakdown(hours=hours)
        
        # Format the results
        formatted = {}
        for protocol, data in results.items():
            formatted[protocol] = {
                'tx_bytes': data['tx_bytes'],
                'rx_bytes': data['rx_bytes'],
                'tx_formatted': format_bytes(data['tx_bytes']),
                'rx_formatted': format_bytes(data['rx_bytes']),
                'total_bytes': data['tx_bytes'] + data['rx_bytes'],
                'total_formatted': format_bytes(data['tx_bytes'] + data['rx_bytes'])
            }
        
        return jsonify({
            'hours': hours,
            'protocols': formatted
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ip/breakdown')
def get_ip_breakdown():
    """Get bandwidth breakdown by remote IP"""
    hours = request.args.get('hours', default=1, type=int)
    process_name = request.args.get('process', default=None, type=str)
    
    try:
        results = storage_instance.get_ip_breakdown(process_name=process_name, hours=hours)
        
        # Format the results
        for result in results:
            result['total_tx_formatted'] = format_bytes(result['total_tx'])
            result['total_rx_formatted'] = format_bytes(result['total_rx'])
            result['total_bytes'] = result['total_tx'] + result['total_rx']
            result['total_formatted'] = format_bytes(result['total_bytes'])
        
        return jsonify({
            'hours': hours,
            'process_name': process_name,
            'ips': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timeseries')
def get_time_series():
    """Get time series data for charts"""
    hours = request.args.get('hours', default=1, type=int)
    interval = request.args.get('interval', default=5, type=int)
    process_name = request.args.get('process', default=None, type=str)
    
    try:
        results = storage_instance.get_time_series(
            process_name=process_name,
            hours=hours,
            interval_minutes=interval
        )
        
        return jsonify({
            'hours': hours,
            'interval_minutes': interval,
            'process_name': process_name,
            'data': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary')
def get_summary():
    """Get summary statistics"""
    hours = request.args.get('hours', default=1, type=int)
    
    try:
        results = storage_instance.get_summary_stats(hours=hours)
        
        results['total_tx_formatted'] = format_bytes(results['total_tx'] or 0)
        results['total_rx_formatted'] = format_bytes(results['total_rx'] or 0)
        results['total_bandwidth'] = (results['total_tx'] or 0) + (results['total_rx'] or 0)
        results['total_bandwidth_formatted'] = format_bytes(results['total_bandwidth'])
        
        return jsonify({
            'hours': hours,
            'stats': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_data():
    """Clean up old records"""
    days = request.json.get('days', 7)
    
    try:
        storage_instance.cleanup_old_records(days=days)
        return jsonify({'success': True, 'message': f'Cleaned up records older than {days} days'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def start_web_server(tracker, host='0.0.0.0', port=8080, debug=False):
    """Start the Flask web server"""
    global tracker_instance, storage_instance
    tracker_instance = tracker
    storage_instance = tracker.storage
    
    print(f"Starting web server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == "__main__":
    # For testing purposes
    storage_instance = BandwidthStorage("bandwidth.db")
    app.run(host='0.0.0.0', port=8080, debug=True)

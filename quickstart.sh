#!/bin/bash

# Quick start script for eBPF Bandwidth Tracker
# This script helps you get started quickly

echo "========================================="
echo "eBPF Bandwidth Tracker - Quick Start"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "⚠ This script needs to be run with sudo"
    echo ""
    echo "Usage: sudo ./quickstart.sh"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check basic requirements
echo "Checking requirements..."

if ! command_exists python3; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found"

# Check if BCC is installed
if ! python3 -c "import bcc" 2>/dev/null; then
    echo "⚠ BCC is not installed. Would you like to install it now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Running installation script..."
        bash install.sh
    else
        echo "Please install BCC manually: https://github.com/iovisor/bcc/blob/master/INSTALL.md"
        exit 1
    fi
else
    echo "✓ BCC found"
fi

# Install Python dependencies if needed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
    pip3 install tabulate
fi

echo "✓ All requirements met"
echo ""

# Menu
echo "Choose an option:"
echo "  1) Start with Web UI (Recommended)"
echo "  2) Start with CLI only"
echo "  3) View historical data"
echo "  4) Run system check"
echo "  5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "Starting eBPF Bandwidth Tracker with Web UI..."
        echo "Access the dashboard at: http://localhost:8080"
        echo ""
        echo "Press Ctrl+C to stop"
        echo ""
        python3 ebpf_tracker.py --web
        ;;
    2)
        echo ""
        echo "Starting eBPF Bandwidth Tracker (CLI mode)..."
        echo "Press Ctrl+C to stop"
        echo ""
        python3 cli.py --live --interval 2
        ;;
    3)
        echo ""
        echo "Historical Data - Top 20 Processes (Last 24 hours)"
        echo ""
        python3 cli.py --history --hours 24 --top 20
        echo ""
        read -p "Press Enter to continue..."
        ;;
    4)
        echo ""
        echo "System Check"
        echo "============"
        echo ""
        echo "Kernel Version: $(uname -r)"
        echo ""
        echo "BCC Installation:"
        python3 -c "import bcc; print('  Version:', bcc.__version__)" 2>/dev/null || echo "  Not installed"
        echo ""
        echo "Python Packages:"
        python3 -c "import flask; print('  Flask:', flask.__version__)"
        python3 -c "import bcc; print('  BCC: Installed')" 2>/dev/null || echo "  BCC: Not installed"
        echo ""
        echo "eBPF Support:"
        grep CONFIG_BPF /boot/config-$(uname -r) 2>/dev/null | head -5 || echo "  Unable to check"
        echo ""
        echo "Required Kernel Functions:"
        for func in tcp_sendmsg tcp_recvmsg udp_sendmsg udp_recvmsg; do
            if grep -q "$func" /proc/kallsyms 2>/dev/null; then
                echo "  ✓ $func"
            else
                echo "  ❌ $func (may not be available)"
            fi
        done
        echo ""
        read -p "Press Enter to continue..."
        ;;
    5)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting..."
        exit 1
        ;;
esac

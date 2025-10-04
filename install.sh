#!/bin/bash

# Installation script for eBPF Bandwidth Tracker
# This script installs all dependencies and sets up the tracker

set -e

echo "========================================"
echo "eBPF Bandwidth Tracker - Installation"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "Cannot detect OS. Please install manually."
    exit 1
fi

echo "Detected OS: $OS $VERSION"
echo ""

# Install system dependencies
echo "Step 1: Installing system dependencies..."

if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ] || [ "$OS" = "linuxmint" ]; then
    apt-get update
    apt-get install -y \
        build-essential \
        linux-headers-$(uname -r) \
        bpfcc-tools \
        python3-bpfcc \
        python3-pip \
        python3-venv \
        sqlite3 \
        git
    
    echo "✓ System dependencies installed"
    
elif [ "$OS" = "fedora" ] || [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
    dnf install -y \
        kernel-devel \
        kernel-headers \
        bcc-tools \
        python3-bcc \
        python3-pip \
        sqlite \
        git
    
    echo "✓ System dependencies installed"
    
else
    echo "Unsupported OS: $OS"
    echo "Please install BCC tools manually: https://github.com/iovisor/bcc/blob/master/INSTALL.md"
    exit 1
fi

# Create Python virtual environment (optional but recommended)
echo ""
echo "Step 2: Setting up Python environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv --system-site-packages
    echo "✓ Virtual environment created"
fi

source venv/bin/activate

# Install Python dependencies
echo ""
echo "Step 3: Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r requirements.txt
pip3 install tabulate  # For CLI pretty printing

echo "✓ Python packages installed"

# Verify eBPF support
echo ""
echo "Step 4: Verifying eBPF support..."

KERNEL_VERSION=$(uname -r | cut -d'.' -f1,2)
REQUIRED_VERSION=4.15

if awk "BEGIN {exit !($KERNEL_VERSION >= $REQUIRED_VERSION)}"; then
    echo "✓ Kernel version $KERNEL_VERSION is compatible (>= $REQUIRED_VERSION)"
else
    echo "⚠ Warning: Kernel version $KERNEL_VERSION may not fully support eBPF"
    echo "  Recommended kernel version: 4.15 or higher"
fi

# Check if BPF filesystem is mounted
if mount | grep -q bpf; then
    echo "✓ BPF filesystem is mounted"
else
    echo "⚠ Warning: BPF filesystem not mounted"
    echo "  Mounting BPF filesystem..."
    mount -t bpf bpf /sys/fs/bpf/
fi

# Create database directory
echo ""
echo "Step 5: Setting up database..."
mkdir -p data
echo "✓ Database directory created"

# Make scripts executable
echo ""
echo "Step 6: Setting permissions..."
chmod +x ebpf_tracker.py
chmod +x cli.py
chmod +x install.sh
echo "✓ Scripts made executable"

# # Create systemd service (optional)
# echo ""
# echo "Step 7: Creating systemd service (optional)..."

# cat > /etc/systemd/system/ebpf-bandwidth-tracker.service << EOF
# [Unit]
# Description=eBPF Per-Process Bandwidth Tracker
# After=network.target

# [Service]
# Type=simple
# User=root
# WorkingDirectory=$(pwd)
# ExecStart=$(pwd)/venv/bin/python3 $(pwd)/ebpf_tracker.py --web --db $(pwd)/data/bandwidth.db
# Restart=always
# RestartSec=10

# [Install]
# WantedBy=multi-user.target
# EOF

# systemctl daemon-reload
# echo "✓ Systemd service created"
# echo "  To enable and start: sudo systemctl enable --now ebpf-bandwidth-tracker"

# Installation complete
echo ""
echo "========================================"
echo "Installation Complete! ✓"
echo "========================================"
echo ""
echo "Quick Start:"
echo "  1. Start the tracker with web UI:"
echo "     sudo python3 ebpf_tracker.py --web"
echo ""
echo "  2. Access the web interface:"
echo "     http://localhost:8080"
echo ""
echo "  3. Or use the CLI:"
echo "     sudo python3 cli.py --live"
echo ""
echo "  4. View historical data:"
echo "     sudo python3 cli.py --history --hours 24"
echo ""
echo "For more information, see README.md"
echo ""
